from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from core.models import Comentario
from core.serializers.comentario import ComentarioSerializer


class ComentarioViewSet(viewsets.ModelViewSet):
    serializer_class = ComentarioSerializer

    def get_queryset(self):
        usuario = self.request.user

        return Comentario.objects.filter(
            tarefa__projeto__participantes__usuario=usuario
        ).select_related(
            'autor',
            'tarefa',
            'tarefa__projeto',
        ).distinct()

    def perform_update(self, serializer):
        comentario = self.get_object()
        usuario = self.request.user

        eh_admin = comentario.tarefa.projeto.participantes.filter(
            usuario=usuario,
            papel='admin',
        ).exists()

        if comentario.autor != usuario and not eh_admin:
            raise PermissionDenied(
                'Somente o autor ou um administrador pode editar este comentário.'
            )

        serializer.save()

    def perform_destroy(self, instance):
        usuario = self.request.user

        eh_admin = instance.tarefa.projeto.participantes.filter(
            usuario=usuario,
            papel='admin',
        ).exists()

        if instance.autor != usuario and not eh_admin:
            raise PermissionDenied(
                'Somente o autor ou um administrador pode excluir este comentário.'
            )

        instance.delete()