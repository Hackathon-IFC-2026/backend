import hmac
import logging
import secrets
import smtplib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.db import DatabaseError, transaction
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import salted_hmac

from core.models import PasswordResetChallenge, User

logger = logging.getLogger(__name__)

CODE_LIFETIME = timedelta(minutes=10)
REQUEST_WINDOW = timedelta(hours=1)
RESEND_INTERVAL = timedelta(minutes=1)
MAX_REQUESTS_PER_WINDOW = 3
MAX_CODE_ATTEMPTS = 5


class _EmailDeliveryFailed(Exception):
    """Abort challenge persistence when the email cannot be prepared or sent."""


def _active_user_for_email(email, *, lock=False):
    users = User.objects.filter(email__iexact=email, is_active=True)
    if lock:
        users = users.select_for_update()
    matches = list(users[:2])
    return matches[0] if len(matches) == 1 else None


def _code_digest(user, code, created_at):
    value = f'{user.pk}:{created_at.isoformat()}:{code}'
    return salted_hmac(
        'core.password_reset.challenge',
        value,
        secret=settings.SECRET_KEY,
        algorithm='sha256',
    ).hexdigest()


def _send_reset_email(email, code, account_id):
    context = {'code': code, 'expires_in_minutes': int(CODE_LIFETIME.total_seconds() // 60)}
    try:
        text_body = render_to_string('core/emails/password_reset.txt', context)
        html_body = render_to_string('core/emails/password_reset.html', context)
    except (TemplateDoesNotExist, TemplateSyntaxError) as exc:
        logger.error(
            'password_reset stage=template account_id=%s exception=%s',
            account_id,
            type(exc).__name__,
        )
        raise _EmailDeliveryFailed from exc

    message = EmailMultiAlternatives(
        subject='Recuperação de senha',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    message.attach_alternative(html_body, 'text/html')

    try:
        sent_count = message.send(fail_silently=False)
    except (OSError, smtplib.SMTPException, ImproperlyConfigured, ValueError) as exc:
        smtp_code = getattr(exc, 'smtp_code', None)
        errno = getattr(exc, 'errno', None)
        logger.error(
            'password_reset stage=smtp account_id=%s exception=%s smtp_code=%s errno=%s',
            account_id,
            type(exc).__name__,
            smtp_code,
            errno,
        )
        raise _EmailDeliveryFailed from exc

    if sent_count != 1:
        logger.error(
            'password_reset stage=smtp account_id=%s result=no_message_accepted',
            account_id,
        )
        raise _EmailDeliveryFailed

    logger.info('password_reset stage=smtp account_id=%s result=message_accepted', account_id)
    return True


def _request_password_reset(email, now, request_context):
    with transaction.atomic():
        user = _active_user_for_email(email, lock=True)
        if user is None:
            logger.info('password_reset stage=account result=unavailable')
            return False
        user_id = user.pk
        request_context['account_id'] = user_id

        challenge = PasswordResetChallenge.objects.select_for_update().filter(user=user).first()
        if challenge is None:
            challenge = PasswordResetChallenge(user=user)
            challenge.save()

        if now - challenge.request_window_started_at >= REQUEST_WINDOW:
            challenge.request_window_started_at = now
            challenge.requests_in_window = 0
        elif challenge.requests_in_window >= MAX_REQUESTS_PER_WINDOW:
            logger.warning(
                'password_reset stage=throttle account_id=%s reason=request_limit',
                user_id,
            )
            return False

        if challenge.requests_in_window and now - challenge.created_at < RESEND_INTERVAL:
            logger.warning(
                'password_reset stage=throttle account_id=%s reason=resend_cooldown',
                user_id,
            )
            return False

        code = f'{secrets.randbelow(1_000_000):06d}'
        challenge.code_hash = _code_digest(user, code, now)
        challenge.created_at = now
        challenge.expires_at = now + CODE_LIFETIME
        challenge.attempts = 0
        challenge.used_at = None
        challenge.requests_in_window += 1
        challenge.save()

        _send_reset_email(user.email, code, user_id)
        logger.info('password_reset stage=request result=sent account_id=%s', user_id)
    return True


def request_password_reset(email):
    now = timezone.now()
    request_context = {}
    try:
        return _request_password_reset(email, now, request_context)
    except _EmailDeliveryFailed:
        logger.warning(
            'password_reset stage=request result=rolled_back account_id=%s',
            request_context.get('account_id'),
        )
        return False
    except DatabaseError as exc:
        logger.error(
            'password_reset stage=database exception=%s account_id=%s',
            type(exc).__name__,
            request_context.get('account_id'),
        )
        return False


def _valid_challenge(challenge, code, now):
    if challenge.used_at is not None or challenge.expires_at is None:
        return False
    if challenge.expires_at <= now:
        challenge.used_at = now
        challenge.save(update_fields=['used_at'])
        return False
    if challenge.attempts >= MAX_CODE_ATTEMPTS:
        return False
    if not hmac.compare_digest(
        challenge.code_hash,
        _code_digest(challenge.user, code, challenge.created_at),
    ):
        challenge.attempts += 1
        challenge.save(update_fields=['attempts'])
        return False
    return True


def verify_password_reset_code(email, code):
    with transaction.atomic():
        user = _active_user_for_email(email, lock=True)
        if user is None:
            return False

        challenge = PasswordResetChallenge.objects.select_for_update().filter(user=user).first()
        return challenge is not None and _valid_challenge(challenge, code, timezone.now())


def reset_password(email, code, new_password):
    with transaction.atomic():
        user = _active_user_for_email(email, lock=True)
        if user is None:
            return False

        challenge = PasswordResetChallenge.objects.select_for_update().filter(user=user).first()
        if challenge is None or not _valid_challenge(challenge, code, timezone.now()):
            return False

        validate_password(new_password, user=user)
        user.set_password(new_password)
        user.save(update_fields=['password'])
        challenge.used_at = timezone.now()
        challenge.save(update_fields=['used_at'])
    return True
