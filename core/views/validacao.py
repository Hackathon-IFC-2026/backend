from core.serializers.validacao import ValidacaoSerializer
from rest_framework.viewsets import ModelViewSet

from core.models import Validacao
from core.serializers import ValidacaoSerializer


class ValidacaoViewSet(ModelViewSet):
    queryset = Validacao.objects.all()
    serializer_class = ValidacaoSerializer
