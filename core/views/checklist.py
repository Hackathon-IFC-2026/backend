from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Checklist
from core.project_permissions import ChecklistPermission, projetos_visiveis
from core.serializers import ChecklistSerializer


class ChecklistViewSet(ModelViewSet):
    queryset = Checklist.objects.none()
    serializer_class = ChecklistSerializer
    permission_classes = [IsAuthenticated, ChecklistPermission]

    def get_queryset(self):
        qs = (
            Checklist.objects
            .filter(tarefa__projeto__in=projetos_visiveis(self.request.user))
            .select_related('tarefa__projeto')
            .order_by('ordem', 'id')
        )
        value = self.request.query_params.get('tarefa')
        if value:
            if not value.isdigit():
                raise ValidationError({'tarefa': 'ID inválido.'})
            qs = qs.filter(tarefa_id=value)
        return qs
