from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from core.models import Task
from core.serializers.task import TaskSerializer


class TaskPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user.pk in {obj.created_by_id, obj.board.owner_id} or (
                obj.participants.filter(pk=request.user.pk).exists()
            )
        return request.user.pk in {obj.created_by_id, obj.board.owner_id}


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = (permissions.IsAuthenticated, TaskPermissions)

    def get_queryset(self):
        return (
            Task.objects
            .filter(
                Q(created_by=self.request.user) | Q(board__owner=self.request.user) | Q(participants=self.request.user)
            )
            .distinct()
            .select_related('board', 'created_by', 'assignee')
            .prefetch_related('participants')
        )

    def perform_create(self, serializer):
        board = serializer.validated_data['board']
        if board.owner_id != self.request.user.pk:
            raise PermissionDenied('Somente o proprietário do quadro pode criar tarefas nele.')
        serializer.save(created_by=self.request.user)
