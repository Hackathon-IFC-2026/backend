from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from core.models import Checklist
from core.serializers.checklist import ChecklistSerializer


class ChecklistViewSet(viewsets.ModelViewSet):
    serializer_class = ChecklistSerializer

    def get_queryset(self):
        usuario = self.request.user

        return Checklist.objects.filter(
            tarefa__projeto__participantes__usuario=usuario
        ).select_related(
            'tarefa',
            'tarefa__projeto',
        ).distinct()

    def pode_editar(self, tarefa):
        usuario = self.request.user

        eh_admin = tarefa.projeto.participantes.filter(
            usuario=usuario,
            papel='admin',
        ).exists()

        return (
            eh_admin
            or tarefa.criador_id == usuario.id
            or tarefa.responsavel_id == usuario.id
        )

    def perform_create(self, serializer):
        tarefa = serializer.validated_data['tarefa']

        if tarefa.bloqueada:
            raise PermissionDenied(
                'Não é possível adicionar itens a uma tarefa bloqueada.'
            )

        if not self.pode_editar(tarefa):
            raise PermissionDenied(
                'Você não tem permissão para alterar o checklist desta tarefa.'
            )

        serializer.save()

    def perform_update(self, serializer):
        checklist = self.get_object()
        tarefa = checklist.tarefa

        if tarefa.bloqueada:
            raise PermissionDenied(
                'Não é possível alterar o checklist de uma tarefa bloqueada.'
            )

        if not self.pode_editar(tarefa):
            raise PermissionDenied(
                'Você não tem permissão para alterar o checklist desta tarefa.'
            )

        serializer.save()

    def perform_destroy(self, instance):
        tarefa = instance.tarefa

        if tarefa.bloqueada:
            raise PermissionDenied(
                'Não é possível excluir itens de uma tarefa bloqueada.'
            )

        if not self.pode_editar(tarefa):
            raise PermissionDenied(
                'Você não tem permissão para excluir este item do checklist.'
            )

        instance.delete()