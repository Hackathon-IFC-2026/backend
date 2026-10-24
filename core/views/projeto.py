from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Projeto
from core.serializers import ProjetoSerializer


class ProjetoViewSet(ModelViewSet):
    queryset = Projeto.objects.all().order_by('criado_em')
    serializer_class = ProjetoSerializer
    permission_classes = [IsAuthenticated]
