from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from core.models import MaterialApoio
from core.serializers.material_apoio import MaterialApoioSerializer


class MaterialApoioViewSet(viewsets.ModelViewSet):
    serializer_class = MaterialApoioSerializer

    def get_queryset(self):
        usuario = self.request.user

        return MaterialApoio.objects.filter(
            projeto__participantes__usuario=usuario
        ).select_related(
            'projeto',
            'criador',
        ).distinct()

    def perform_update(self, serializer):
        material = self.get_object()
        usuario = self.request.user

        eh_admin = material.projeto.participantes.filter(
            usuario=usuario,
            papel='admin',
        ).exists()

        if material.criador != usuario and not eh_admin:
            raise PermissionDenied(
                'Somente o criador ou um administrador pode editar este material.'
            )

        serializer.save()

    def perform_destroy(self, instance):
        usuario = self.request.user

        eh_admin = instance.projeto.participantes.filter(
            usuario=usuario,
            papel='admin',
        ).exists()

        if instance.criador != usuario and not eh_admin:
            raise PermissionDenied(
                'Somente o criador ou um administrador pode excluir este material.'
            )

        instance.delete()