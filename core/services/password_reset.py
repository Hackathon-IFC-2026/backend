import hmac
import logging
import secrets
import smtplib
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives, get_connection
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
SMTP_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'


class _EmailDeliveryFailed(Exception):
    """Abort challenge persistence when the email cannot be prepared or sent."""


def _log_email_failure(stage, flow_id, exc):
    smtp_code = getattr(exc, 'smtp_code', None)
    errno = getattr(exc, 'errno', None)
    refused_recipients = getattr(exc, 'recipients', {})
    refused_codes = sorted(
        {
            response[0]
            for response in refused_recipients.values()
            if isinstance(response, tuple)
            and response
            and isinstance(response[0], int)
        }
    )
    if not isinstance(smtp_code, int):
        smtp_code = refused_codes[0] if len(refused_codes) == 1 else None
    if not isinstance(errno, int):
        errno = None
    logger.error(
        'password_reset flow_id=%s stage=%s result=failed reason=%s exception=%s '
        'smtp_code=%s errno=%s refused_recipient_count=%s refused_recipient_codes=%s',
        flow_id,
        stage,
        stage,
        type(exc).__name__,
        smtp_code,
        errno,
        len(refused_recipients),
        ','.join(str(code) for code in refused_codes) or None,
    )


def _close_smtp_connection(connection, flow_id):
    try:
        connection.close()
    except (OSError, smtplib.SMTPException) as exc:
        _log_email_failure('smtp_close', flow_id, exc)


def _active_user_for_email(email, *, lock=False):
    users = User.objects.filter(email__iexact=email)
    if lock:
        users = users.select_for_update()
    if not users.exists():
        return None, 'not_found'

    active_users = list(users.filter(is_active=True)[:2])
    if not active_users:
        return None, 'inactive'
    if len(active_users) > 1:
        return None, 'ambiguous'
    return active_users[0], None


def _code_digest(user, code, created_at):
    value = f'{user.pk}:{created_at.isoformat()}:{code}'
    return salted_hmac(
        'core.password_reset.challenge',
        value,
        secret=settings.SECRET_KEY,
        algorithm='sha256',
    ).hexdigest()


def _send_reset_email(email, code, flow_id):
    context = {'code': code, 'expires_in_minutes': int(CODE_LIFETIME.total_seconds() // 60)}
    try:
        text_body = render_to_string('core/emails/password_reset.txt', context)
        html_body = render_to_string('core/emails/password_reset.html', context)
    except (TemplateDoesNotExist, TemplateSyntaxError) as exc:
        logger.error(
            'password_reset flow_id=%s stage=template result=failed reason=render_error exception=%s',
            flow_id,
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
    logger.info('password_reset flow_id=%s stage=message result=prepared', flow_id)

    smtp_connection = None
    if settings.EMAIL_BACKEND == SMTP_BACKEND:
        try:
            smtp_connection = get_connection(fail_silently=False)
            smtp_connection.open()
        except (OSError, smtplib.SMTPException, ImproperlyConfigured, ValueError) as exc:
            if smtp_connection is not None:
                _close_smtp_connection(smtp_connection, flow_id)
            _log_email_failure('smtp_connection_or_authentication', flow_id, exc)
            raise _EmailDeliveryFailed from exc
        message.connection = smtp_connection

    logger.info(
        'password_reset flow_id=%s stage=email_backend result=submission_started backend=%s',
        flow_id,
        settings.EMAIL_BACKEND,
    )
    try:
        sent_count = message.send(fail_silently=False)
    except (OSError, smtplib.SMTPException, ImproperlyConfigured, ValueError) as exc:
        stage = 'smtp_submission' if smtp_connection is not None else 'email_backend'
        _log_email_failure(stage, flow_id, exc)
        raise _EmailDeliveryFailed from exc
    finally:
        if smtp_connection is not None:
            _close_smtp_connection(smtp_connection, flow_id)

    if sent_count != 1:
        stage = 'smtp_submission' if smtp_connection is not None else 'email_backend'
        logger.error(
            'password_reset flow_id=%s stage=%s result=not_accepted reason=backend_rejected_message',
            flow_id,
            stage,
        )
        raise _EmailDeliveryFailed

    result = 'accepted_by_smtp' if smtp_connection is not None else 'accepted_by_backend'
    logger.info(
        'password_reset flow_id=%s stage=email_backend result=%s backend=%s',
        flow_id,
        result,
        settings.EMAIL_BACKEND,
    )
    return True


def _request_password_reset(email, now, flow_id, *, allow_repeated_requests=False):
    with transaction.atomic():
        user, unavailable_reason = _active_user_for_email(email, lock=True)
        if user is None:
            logger.info(
                'password_reset flow_id=%s stage=account result=unavailable reason=%s',
                flow_id,
                unavailable_reason,
            )
            return False
        logger.info('password_reset flow_id=%s stage=account result=eligible', flow_id)

        challenge = PasswordResetChallenge.objects.select_for_update().filter(user=user).first()
        if challenge is None:
            challenge = PasswordResetChallenge(user=user)
            challenge.save()

        if now - challenge.request_window_started_at >= REQUEST_WINDOW:
            challenge.request_window_started_at = now
            challenge.requests_in_window = 0
        elif not allow_repeated_requests and challenge.requests_in_window >= MAX_REQUESTS_PER_WINDOW:
            logger.warning(
                'password_reset flow_id=%s stage=throttle result=blocked reason=request_limit',
                flow_id,
            )
            return False

        if (
            not allow_repeated_requests
            and challenge.requests_in_window
            and now - challenge.created_at < RESEND_INTERVAL
        ):
            logger.warning(
                'password_reset flow_id=%s stage=throttle result=blocked reason=resend_cooldown',
                flow_id,
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
        logger.info(
            'password_reset flow_id=%s stage=challenge result=generated_and_saved_in_transaction',
            flow_id,
        )

        _send_reset_email(user.email, code, flow_id)
    logger.info(
        'password_reset flow_id=%s stage=request result=challenge_committed_after_backend_acceptance',
        flow_id,
    )
    return True


def request_password_reset(email, *, allow_repeated_requests=False):
    flow_id = secrets.token_hex(8)
    logger.info('password_reset flow_id=%s stage=request result=received', flow_id)
    now = timezone.now()
    try:
        return _request_password_reset(
            email,
            now,
            flow_id,
            allow_repeated_requests=allow_repeated_requests,
        )
    except _EmailDeliveryFailed:
        logger.warning(
            'password_reset flow_id=%s stage=request result=challenge_rolled_back reason=email_delivery_failed',
            flow_id,
        )
        return False
    except DatabaseError as exc:
        logger.error(
            'password_reset flow_id=%s stage=database result=failed exception=%s',
            flow_id,
            type(exc).__name__,
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
        user, _ = _active_user_for_email(email, lock=True)
        if user is None:
            return False

        challenge = PasswordResetChallenge.objects.select_for_update().filter(user=user).first()
        return challenge is not None and _valid_challenge(challenge, code, timezone.now())


def reset_password(email, code, new_password):
    with transaction.atomic():
        user, _ = _active_user_for_email(email, lock=True)
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
