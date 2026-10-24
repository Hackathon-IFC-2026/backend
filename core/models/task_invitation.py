import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from core.models.task import Task


class TaskInvitation(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pendente'
        ACCEPTED = 'accepted', 'Aceito'
        DECLINED = 'declined', 'Recusado'
        EXPIRED = 'expired', 'Expirado'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='invitations')
    invitee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='task_invitations',
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_task_invitations',
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('task', 'invitee'),
                condition=Q(status='pending'),
                name='unique_pending_task_invitation',
            ),
        ]

    def __str__(self):
        return f'{self.task}: {self.invitee_id} ({self.status})'
