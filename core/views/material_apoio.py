from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import MaterialApoio
from core.serializers import MaterialApoioSerializer


class MaterialApoioViewSet(ModelViewSet):
    queryset = MaterialApoio.objects.all().order_by('criado_em')
    serializer_class = MaterialApoioSerializer
    permission_classes = [IsAuthenticated]
