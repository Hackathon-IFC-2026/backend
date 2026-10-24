from django.db import transaction
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Projeto, Tarefa
from core.project_permissions import TarefaPermission, administra, edita_tarefa, participa, projetos_visiveis
from core.serializers import TarefaSerializer


class TarefaViewSet(ModelViewSet):
    queryset = Tarefa.objects.none()
    serializer_class = TarefaSerializer
    permission_classes = [IsAuthenticated, TarefaPermission]

    def get_queryset(self):
        qs = (
            Tarefa.objects
            .filter(projeto__in=projetos_visiveis(self.request.user))
            .select_related('projeto', 'responsavel')
            .order_by('posicao', 'criada_em', 'id')
        )
        projeto = self.request.query_params.get('projeto')
        if projeto:
            if not projeto.isdigit():
                raise ValidationError({'projeto': 'ID inválido.'})
            qs = qs.filter(projeto_id=projeto)
        return qs

    @action(detail=True, methods=['get'], url_path='redistribuicoes')
    def redistribuicoes(self, request, pk=None):
        tarefa = self.get_object()
        return Response(list(tarefa.redistribuicoes.values('id', 'anterior_id', 'novo_id', 'autor_id', 'criada_em')))

    @transaction.atomic
    def perform_create(self, serializer):
        projeto = Projeto.objects.select_for_update().get(pk=serializer.validated_data['projeto'].pk)
        if not administra(projeto, self.request.user):
            raise PermissionDenied('Somente administradores podem criar tarefas.')
        responsavel = serializer.validated_data.get('responsavel')
        if responsavel and not participa(projeto, responsavel):
            raise ValidationError({'responsavel': 'O responsável precisa participar do projeto.'})
        serializer.save()

    @transaction.atomic
    def perform_update(self, serializer):
        projeto = Projeto.objects.select_for_update().get(pk=serializer.instance.projeto_id)
        tarefa = Tarefa.objects.select_for_update().get(pk=serializer.instance.pk)
        if not edita_tarefa(tarefa, self.request.user):
            raise PermissionDenied('Você não pode editar esta tarefa.')
        if 'responsavel' in serializer.validated_data and not administra(projeto, self.request.user):
            if serializer.validated_data['responsavel'] != tarefa.responsavel:
                raise PermissionDenied('Somente administradores podem alterar responsáveis.')
        responsavel = serializer.validated_data.get('responsavel')
        if responsavel and not participa(projeto, responsavel):
            raise ValidationError({'responsavel': 'O responsável precisa participar do projeto.'})
        anterior = tarefa.responsavel_id
        serializer.instance = tarefa
        serializer.validate(serializer.validated_data.copy())
        salva = serializer.save()
        if anterior != salva.responsavel_id:
            from core.models import Redistribuicao
            from core.services.notificacoes import notificar
            Redistribuicao.objects.create(tarefa=salva, anterior_id=anterior,
                                         novo_id=salva.responsavel_id, autor=self.request.user)
            if anterior:
                notificar(anterior, 'redistribuicao',
                          f'A tarefa {salva.titulo} foi transferida para outro responsável no projeto {projeto.nome}.',
                          projeto, salva)

    @transaction.atomic
    def perform_destroy(self, instance):
        Projeto.objects.select_for_update().get(pk=instance.projeto_id)
        instance.refresh_from_db()
        if not edita_tarefa(instance, self.request.user):
            raise PermissionDenied('Você não pode excluir esta tarefa.')
        instance.delete()
