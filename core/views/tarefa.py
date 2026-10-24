from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from core.models import Tarefa
from core.serializers.tarefa import TarefaSerializer


class TarefaViewSet(viewsets.ModelViewSet):
    serializer_class = TarefaSerializer

    def get_queryset(self):
        usuario = self.request.user

        return Tarefa.objects.filter(
            projeto__participantes__usuario=usuario
        ).select_related(
            'projeto',
            'criador',
            'responsavel',
        ).distinct()

    def eh_admin(self, tarefa):
        return tarefa.projeto.participantes.filter(
            usuario=self.request.user,
            papel='admin',
        ).exists()

    def pode_editar(self, tarefa):
        usuario = self.request.user

        return (
            self.eh_admin(tarefa)
            or tarefa.criador_id == usuario.id
            or tarefa.responsavel_id == usuario.id
        )

    def perform_create(self, serializer):
        projeto = serializer.validated_data['projeto']
        usuario = self.request.user

        participa = projeto.participantes.filter(
            usuario=usuario
        ).exists()

        if not participa:
            raise PermissionDenied(
                'Você precisa participar do projeto para criar tarefas.'
            )

        serializer.save()

    def perform_update(self, serializer):
        tarefa = self.get_object()
        usuario = self.request.user
        eh_admin = self.eh_admin(tarefa)

        if tarefa.bloqueada:
            # A serializer permite somente atribuir um novo responsável.
            serializer.save()
            return

        if not self.pode_editar(tarefa):
            raise PermissionDenied(
                'Você só pode editar tarefas que criou ou pelas quais é responsável.'
            )

        responsavel_enviado = (
            'responsavel' in serializer.validated_data
            and serializer.validated_data['responsavel'] != tarefa.responsavel
        )

        if responsavel_enviado and not eh_admin:
            raise PermissionDenied(
                'Somente administradores podem alterar o responsável.'
            )

        serializer.save()

    def perform_destroy(self, instance):
        if instance.bloqueada:
            raise PermissionDenied(
                'Esta tarefa está bloqueada e não pode ser excluída.'
            )

        if not self.pode_editar(instance):
            raise PermissionDenied(
                'Você só pode excluir tarefas que criou ou pelas quais é responsável.'
            )

        instance.delete()
