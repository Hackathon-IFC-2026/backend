from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import ParticipanteProjeto
from core.serializers import ParticipanteProjetoSerializer


class ParticipanteProjetoViewSet(ModelViewSet):
    queryset = ParticipanteProjeto.objects.all().order_by('entrou_em')
    serializer_class = ParticipanteProjetoSerializer
    permission_classes = [IsAuthenticated]
