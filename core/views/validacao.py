from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Validacao
from core.serializers import ValidacaoSerializer


class ValidacaoViewSet(ModelViewSet):
    queryset = Validacao.objects.all().order_by('id')
    serializer_class = ValidacaoSerializer
    permission_classes = [IsAuthenticated]
