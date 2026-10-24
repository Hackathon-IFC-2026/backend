from django.conf import settings
from django.db import models


class GoogleDriveCredential(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_drive_credential',
    )
    encrypted_credentials = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)


class GoogleDriveOAuthState(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='google_drive_oauth_states',
    )
    state_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()


class TaskDriveAttachment(models.Model):
    task = models.ForeignKey('core.Task', on_delete=models.CASCADE, related_name='drive_attachments')
    drive_file_id = models.CharField(max_length=255)
    name = models.CharField(max_length=1024)
    mime_type = models.CharField(max_length=255)
    size = models.BigIntegerField(null=True, blank=True)
    web_view_link = models.URLField(blank=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='added_drive_attachments',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=('task', 'drive_file_id'),
                name='unique_task_drive_attachment',
            ),
        ]
