import logging
import smtplib
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils import timezone

from core.models import TaskInvitation

logger = logging.getLogger(__name__)
INVITATION_LIFETIME = timedelta(days=7)


class InvitationEmailError(Exception):
    """The task invitation could not be prepared or submitted."""


def _invitation_action_url(invitation_id, action):
    base_url = settings.FRONTEND_BASE_URL
    parsed_url = urlsplit(base_url)
    if parsed_url.scheme != 'https' or not parsed_url.netloc:
        raise ImproperlyConfigured('FRONTEND_BASE_URL must be an HTTPS URL to send task invitations.')
    return f'{base_url}/convites/{invitation_id}/{action}'


def send_task_invitation_email(invitation):
    task = invitation.task
    try:
        context = {
            'inviter_name': invitation.invited_by.name or 'Um membro do Kando',
            'task_title': task.title,
            'board_title': task.board.title,
            'accept_url': _invitation_action_url(invitation.pk, 'aceitar'),
            'decline_url': _invitation_action_url(invitation.pk, 'recusar'),
            'expires_at': invitation.expires_at,
        }
        text_body = render_to_string('core/emails/task_invitation.txt', context)
        html_body = render_to_string('core/emails/task_invitation.html', context)
    except (ImproperlyConfigured, TemplateDoesNotExist, TemplateSyntaxError, ValueError) as exc:
        logger.error(
            'task_invitation stage=template result=failed invitation_id=%s exception=%s',
            invitation.pk,
            type(exc).__name__,
        )
        raise InvitationEmailError from exc

    message = EmailMultiAlternatives(
        subject=f'Convite para a tarefa: {task.title}',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[invitation.invitee.email],
    )
    message.attach_alternative(html_body, 'text/html')
    logger.info('task_invitation stage=message result=prepared invitation_id=%s', invitation.pk)
    try:
        sent_count = message.send(fail_silently=False)
    except (OSError, smtplib.SMTPException, ImproperlyConfigured, ValueError) as exc:
        smtp_code = getattr(exc, 'smtp_code', None)
        if not isinstance(smtp_code, int):
            smtp_code = None
        logger.error(
            'task_invitation stage=email_backend result=failed invitation_id=%s exception=%s smtp_code=%s',
            invitation.pk,
            type(exc).__name__,
            smtp_code,
        )
        raise InvitationEmailError from exc

    if sent_count != 1:
        logger.error('task_invitation stage=email_backend result=not_accepted invitation_id=%s', invitation.pk)
        raise InvitationEmailError

    logger.info('task_invitation stage=email_backend result=accepted invitation_id=%s', invitation.pk)
    return True


def respond_to_task_invitation(invitation, user, response):
    if invitation.invitee_id != user.pk:
        return 'not_found'
    if invitation.status != TaskInvitation.Status.PENDING:
        return 'already_responded'

    now = timezone.now()
    if invitation.expires_at <= now:
        invitation.status = TaskInvitation.Status.EXPIRED
        invitation.save(update_fields=('status',))
        return 'expired'

    invitation.status = response
    invitation.responded_at = now
    invitation.save(update_fields=('status', 'responded_at'))
    if response == TaskInvitation.Status.ACCEPTED:
        invitation.task.participants.add(user)
    return 'accepted' if response == TaskInvitation.Status.ACCEPTED else 'declined'
