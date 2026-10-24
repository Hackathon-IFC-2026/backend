from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Projeto
from core.project_permissions import ProjetoPermission, administra, projetos_visiveis
from core.serializers import ProjetoSerializer


class ProjetoViewSet(ModelViewSet):
    queryset = Projeto.objects.none()
    serializer_class = ProjetoSerializer
    permission_classes = [IsAuthenticated, ProjetoPermission]

    def get_queryset(self):
        return projetos_visiveis(self.request.user).select_related('criado_por').order_by('criado_em', 'id')

    @action(detail=True, methods=['get'], url_path='carga-trabalho')
    def carga_trabalho(self, request, pk=None):
        from core.services.insights import analisar
        return Response(analisar(self.get_object(), request.user))

    @action(detail=True, methods=['get'], url_path='sugestoes-redistribuicao')
    def sugestoes_redistribuicao(self, request, pk=None):
        from core.services.insights import analisar
        projeto = self.get_object()
        if not administra(projeto, request.user):
            raise PermissionDenied('Somente administradores podem analisar a equipe.')
        return Response(analisar(projeto, request.user)['sugestoes'])

    @action(detail=True, methods=['post'], url_path='capacidade')
    @transaction.atomic
    def capacidade(self, request, pk=None):
        from core.models import ParticipanteProjeto
        from rest_framework import serializers
        class Configuracao(serializers.Serializer):
            usuario = serializers.IntegerField(min_value=1)
            capacidade = serializers.IntegerField(min_value=1, max_value=1000)
        projeto = self.get_object()
        projeto = Projeto.objects.select_for_update().get(pk=projeto.pk)
        if not administra(projeto, request.user):
            raise PermissionDenied('Somente administradores podem ajustar a capacidade.')
        dados = Configuracao(data=request.data)
        dados.is_valid(raise_exception=True)
        atualizados = ParticipanteProjeto.objects.filter(
            projeto=projeto, usuario_id=dados.validated_data['usuario'],
        ).update(capacidade=dados.validated_data['capacidade'])
        if not atualizados:
            raise ValidationError({'usuario': 'O usuário precisa participar do projeto.'})
        return Response(dados.validated_data)

    @transaction.atomic
    def perform_update(self, serializer):
        projeto = Projeto.objects.select_for_update().get(pk=serializer.instance.pk)
        if not administra(projeto, self.request.user):
            raise PermissionDenied('Somente administradores podem editar o projeto.')
        serializer.instance = projeto
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        projeto = Projeto.objects.select_for_update().get(pk=instance.pk)
        if not administra(projeto, self.request.user):
            raise PermissionDenied('Somente administradores podem excluir o projeto.')
        projeto.delete()
