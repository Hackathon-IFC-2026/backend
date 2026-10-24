from django.conf import settings
from django.db import models
from django.utils import timezone


class PasswordResetChallenge(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='password_reset_challenge',
    )
    code_hash = models.CharField(max_length=128, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    used_at = models.DateTimeField(null=True, blank=True)
    request_window_started_at = models.DateTimeField(default=timezone.now)
    requests_in_window = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = 'Desafio de recuperação de senha'
        verbose_name_plural = 'Desafios de recuperação de senha'
