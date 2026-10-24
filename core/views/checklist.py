from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Checklist
from core.serializers import ChecklistSerializer


class ChecklistViewSet(ModelViewSet):
    queryset = Checklist.objects.all().order_by('ordem', 'id')
    serializer_class = ChecklistSerializer
    permission_classes = [IsAuthenticated]
