from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Tarefa
from core.serializers import TarefaSerializer


class TarefaViewSet(ModelViewSet):
    queryset = Tarefa.objects.all().order_by('posicao', 'criada_em')
    serializer_class = TarefaSerializer
    permission_classes = [IsAuthenticated]
