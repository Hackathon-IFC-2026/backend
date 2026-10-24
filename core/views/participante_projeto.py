from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import ParticipanteProjeto, Projeto, Tarefa
from core.project_permissions import ProjetoPermission, administra, projetos_visiveis
from core.serializers import ParticipanteProjetoSerializer


class ParticipanteProjetoViewSet(ModelViewSet):
    queryset = ParticipanteProjeto.objects.none()
    serializer_class = ParticipanteProjetoSerializer
    permission_classes = [IsAuthenticated, ProjetoPermission]

    def get_queryset(self):
        qs = (
            ParticipanteProjeto.objects
            .filter(projeto__in=projetos_visiveis(self.request.user))
            .select_related('projeto')
            .order_by('entrou_em', 'id')
        )
        projeto = self.request.query_params.get('projeto')
        if projeto:
            if not projeto.isdigit():
                raise ValidationError({'projeto': 'ID inválido.'})
            qs = qs.filter(projeto_id=projeto)
        return qs

    def bloquear_projeto(self, projeto):
        projeto = Projeto.objects.select_for_update().get(pk=projeto.pk)
        if not administra(projeto, self.request.user):
            raise PermissionDenied('Somente administradores podem gerenciar participantes.')
        return projeto

    @transaction.atomic
    def perform_create(self, serializer):
        self.bloquear_projeto(serializer.validated_data['projeto'])
        serializer.save()

    def verificar_ultimo(self, projeto, instance):
        atual = ParticipanteProjeto.objects.get(pk=instance.pk)
        if atual.papel == 'admin' and projeto.participantes.filter(papel='admin').count() <= 1:
            raise ValidationError({'papel': 'O projeto precisa manter pelo menos um administrador.'})

    @transaction.atomic
    def perform_update(self, serializer):
        projeto = self.bloquear_projeto(serializer.instance.projeto)
        if serializer.validated_data.get('papel', serializer.instance.papel) != 'admin':
            self.verificar_ultimo(projeto, serializer.instance)
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        projeto = self.bloquear_projeto(instance.projeto)
        self.verificar_ultimo(projeto, instance)
        Tarefa.objects.filter(projeto=projeto, responsavel=instance.usuario).update(responsavel=None)
        instance.delete()
