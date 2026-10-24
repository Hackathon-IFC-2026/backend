from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from core.models import Projeto
from core.serializers.projeto import ProjetoSerializer


class ProjetoViewSet(viewsets.ModelViewSet):
    serializer_class = ProjetoSerializer

    def get_queryset(self):
        usuario = self.request.user

        return Projeto.objects.filter(
            participantes__usuario=usuario
        ).distinct()

    def perform_update(self, serializer):
        projeto = self.get_object()
        usuario = self.request.user

        eh_admin = projeto.participantes.filter(
            usuario=usuario,
            papel='admin',
        ).exists()

        if not eh_admin:
            raise PermissionDenied(
                'Somente administradores podem editar o projeto.'
            )

        serializer.save()

    def perform_destroy(self, instance):
        usuario = self.request.user

        eh_admin = instance.participantes.filter(
            usuario=usuario,
            papel='admin',
        ).exists()

        if not eh_admin:
            raise PermissionDenied(
                'Somente administradores podem excluir o projeto.'
            )

        instance.delete()