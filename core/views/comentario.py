from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Comentario
from core.serializers import ComentarioSerializer


class ComentarioViewSet(ModelViewSet):
    queryset = Comentario.objects.all().order_by('criado_em')
    serializer_class = ComentarioSerializer
    permission_classes = [IsAuthenticated]
