from django.db.models import Q
from rest_framework import permissions, viewsets

from core.models import Board
from core.serializers.board import BoardSerializer


class BoardPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return obj.owner_id == request.user.pk or obj.tasks.filter(participants=request.user).exists()
        return obj.owner_id == request.user.pk


class BoardViewSet(viewsets.ModelViewSet):
    serializer_class = BoardSerializer
    permission_classes = (permissions.IsAuthenticated, BoardPermissions)

    def get_queryset(self):
        return (
            Board.objects
            .filter(Q(owner=self.request.user) | Q(tasks__participants=self.request.user))
            .distinct()
            .select_related('owner')
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
