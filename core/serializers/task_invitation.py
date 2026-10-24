from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from core.models import Task, TaskInvitation, User


class TaskInvitationCreateSerializer(serializers.Serializer):
    task = serializers.PrimaryKeyRelatedField(queryset=Task.objects.select_related('board', 'created_by'))
    email = serializers.EmailField()

    def validate_email(self, value):
        invitee = User.objects.filter(email__iexact=value, is_active=True).first()
        if invitee is None:
            raise serializers.ValidationError('O destinatário precisa ter uma conta ativa no Kando.')
        self.context['invitee'] = invitee
        return invitee.email

    def validate(self, attrs):
        task = attrs['task']
        requester = self.context['request'].user
        if requester.pk not in {task.created_by_id, task.board.owner_id}:
            raise PermissionDenied('Você não tem permissão para convidar pessoas para esta tarefa.')

        invitee = self.context['invitee']
        if invitee.pk == requester.pk:
            raise serializers.ValidationError({'email': 'Você já tem acesso à tarefa.'})
        if task.participants.filter(pk=invitee.pk).exists():
            raise serializers.ValidationError({'email': 'Este usuário já participa da tarefa.'})
        attrs['invitee'] = invitee
        return attrs


class TaskInvitationSerializer(serializers.ModelSerializer):
    task_title = serializers.CharField(source='task.title', read_only=True)
    board_title = serializers.CharField(source='task.board.title', read_only=True)
    invited_by_name = serializers.SerializerMethodField()

    class Meta:
        model = TaskInvitation
        fields = (
            'id',
            'task',
            'task_title',
            'board_title',
            'invited_by',
            'invited_by_name',
            'status',
            'created_at',
            'responded_at',
            'expires_at',
        )
        read_only_fields = fields

    def get_invited_by_name(self, obj):
        return obj.invited_by.name or 'Um membro do Kando'
