from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from core.models import ParticipanteProjeto
from core.serializers.participante_projeto import ParticipanteProjetoSerializer


class ParticipanteProjetoViewSet(viewsets.ModelViewSet):
    serializer_class = ParticipanteProjetoSerializer

    def get_queryset(self):
        usuario = self.request.user

        return ParticipanteProjeto.objects.filter(
            projeto__participantes__usuario=usuario
        ).select_related(
            'projeto',
            'usuario',
        ).distinct()

    def perform_create(self, serializer):
        projeto = serializer.validated_data['projeto']
        usuario = self.request.user

        eh_admin = projeto.participantes.filter(
            usuario=usuario,
            papel=ParticipanteProjeto.Papel.ADMIN,
        ).exists()

        if not eh_admin:
            raise PermissionDenied(
                'Somente administradores podem adicionar participantes.'
            )

        serializer.save()

    def perform_update(self, serializer):
        participante = self.get_object()
        usuario = self.request.user

        eh_admin = participante.projeto.participantes.filter(
            usuario=usuario,
            papel=ParticipanteProjeto.Papel.ADMIN,
        ).exists()

        if not eh_admin:
            raise PermissionDenied(
                'Somente administradores podem alterar participantes.'
            )

        serializer.save()

    def perform_destroy(self, instance):
        usuario = self.request.user
        projeto = instance.projeto

        eh_admin = projeto.participantes.filter(
            usuario=usuario,
            papel=ParticipanteProjeto.Papel.ADMIN,
        ).exists()

        if not eh_admin:
            raise PermissionDenied(
                'Somente administradores podem remover participantes.'
            )

        if instance.papel == ParticipanteProjeto.Papel.ADMIN:
            quantidade_admins = projeto.participantes.filter(
                papel=ParticipanteProjeto.Papel.ADMIN
            ).count()

            if quantidade_admins <= 1:
                raise PermissionDenied(
                    'O projeto precisa ter pelo menos um administrador.'
                )

        instance.delete()