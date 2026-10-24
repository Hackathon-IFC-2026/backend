from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Comentario
from core.project_permissions import ComentarioPermission, projetos_visiveis
from core.serializers import ComentarioSerializer


class ComentarioViewSet(ModelViewSet):
    queryset = Comentario.objects.none()
    serializer_class = ComentarioSerializer
    permission_classes = [IsAuthenticated, ComentarioPermission]

    def get_queryset(self):
        qs = (
            Comentario.objects
            .filter(tarefa__projeto__in=projetos_visiveis(self.request.user))
            .select_related('tarefa__projeto')
            .order_by('criado_em', 'id')
        )
        value = self.request.query_params.get('tarefa')
        if value:
            if not value.isdigit():
                raise ValidationError({'tarefa': 'ID inválido.'})
            qs = qs.filter(tarefa_id=value)
        return qs

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)
