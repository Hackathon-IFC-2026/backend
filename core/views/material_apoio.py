from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import MaterialApoio
from core.project_permissions import MaterialPermission, projetos_visiveis
from core.serializers import MaterialApoioSerializer


class MaterialApoioViewSet(ModelViewSet):
    queryset = MaterialApoio.objects.none()
    serializer_class = MaterialApoioSerializer
    permission_classes = [IsAuthenticated, MaterialPermission]

    def get_queryset(self):
        qs = (
            MaterialApoio.objects
            .filter(projeto__in=projetos_visiveis(self.request.user))
            .select_related('projeto')
            .order_by('criado_em', 'id')
        )
        value = self.request.query_params.get('projeto')
        if value:
            if not value.isdigit():
                raise ValidationError({'projeto': 'ID inválido.'})
            qs = qs.filter(projeto_id=value)
        return qs

    def perform_create(self, serializer):
        serializer.save(criador=self.request.user)
