from rest_framework import serializers

from core.models import Board, Task, User


class TaskSerializer(serializers.ModelSerializer):
    board = serializers.PrimaryKeyRelatedField(queryset=Board.objects.all())
    created_by = serializers.PrimaryKeyRelatedField(read_only=True)
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True),
        allow_null=True,
        required=False,
    )
    participants = serializers.PrimaryKeyRelatedField(many=True, read_only=True)

    class Meta:
        model = Task
        fields = (
            'id',
            'board',
            'title',
            'description',
            'status',
            'created_by',
            'assignee',
            'participants',
            'due_at',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_by', 'participants', 'created_at', 'updated_at')
