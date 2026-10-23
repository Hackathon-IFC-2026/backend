import smtplib
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.template import TemplateDoesNotExist
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import PasswordResetChallenge, User


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class PasswordResetAPITests(APITestCase):
    request_url = '/api/auth/password-reset/request/'
    verify_url = '/api/auth/password-reset/verify/'
    confirm_url = '/api/auth/password-reset/confirm/'
    email = 'user@example.com'
    initial_password = 'OldAccountPassword!123'
    new_password = 'CorrectHorseBatteryStaple!92'
    max_attempts = 5
    max_requests_per_account = 3
    max_requests_per_ip = 10
    expected_message_count_after_resend = 2
    sha256_digest_length = 64

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(self.email, self.initial_password)

    def request_code(self, code_number=12345):
        with patch('core.services.password_reset.secrets.randbelow', return_value=code_number):
            return self.client.post(self.request_url, {'email': self.email}, format='json')

    def confirm_payload(self, **overrides):
        payload = {
            'email': self.email,
            'code': '012345',
            'new_password': self.new_password,
            'confirm_password': self.new_password,
        }
        payload.update(overrides)
        return payload

    def test_request_sends_html_and_plain_text_to_registered_address(self):
        response = self.request_code()

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data['detail'] == 'Se a conta existir, enviaremos as instruções para o e-mail cadastrado.'
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == [self.email]
        assert '012345' in message.body
        assert '10 minutos' in message.body
        assert len(message.alternatives) == 1
        assert message.alternatives[0][1] == 'text/html'
        assert '012345' in message.alternatives[0][0]
        challenge = PasswordResetChallenge.objects.get(user=self.user)
        assert challenge.code_hash != '012345'
        assert len(challenge.code_hash) == self.sha256_digest_length

    def test_unknown_email_has_the_same_generic_response_without_sending(self):
        known_response = self.request_code()
        mail.outbox.clear()
        unknown_response = self.client.post(
            self.request_url,
            {'email': 'missing@example.com'},
            format='json',
        )

        assert unknown_response.status_code == known_response.status_code
        assert unknown_response.data == known_response.data
        assert mail.outbox == []

    def test_invalid_email_format_is_rejected(self):
        response = self.client.post(self.request_url, {'email': 'not-an-email'}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_correct_code_verifies_and_wrong_code_is_rejected(self):
        self.request_code()
        wrong_response = self.client.post(
            self.verify_url,
            {'email': self.email, 'code': '999999'},
            format='json',
        )
        valid_response = self.client.post(
            self.verify_url,
            {'email': self.email, 'code': '012345'},
            format='json',
        )

        assert wrong_response.status_code == status.HTTP_400_BAD_REQUEST
        assert valid_response.status_code == status.HTTP_200_OK

    def test_expired_code_is_rejected_and_invalidated(self):
        self.request_code()
        challenge = PasswordResetChallenge.objects.get(user=self.user)
        challenge.expires_at = timezone.now() - timedelta(seconds=1)
        challenge.save(update_fields=['expires_at'])

        response = self.client.post(
            self.verify_url,
            {'email': self.email, 'code': '012345'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        challenge.refresh_from_db()
        assert challenge.used_at is not None

    def test_used_code_is_rejected(self):
        self.request_code()
        challenge = PasswordResetChallenge.objects.get(user=self.user)
        challenge.used_at = timezone.now()
        challenge.save(update_fields=['used_at'])

        response = self.client.post(
            self.verify_url,
            {'email': self.email, 'code': '012345'},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_code_attempt_limit_is_enforced(self):
        self.request_code()
        for _ in range(self.max_attempts):
            response = self.client.post(
                self.verify_url,
                {'email': self.email, 'code': '999999'},
                format='json',
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

        correct_response = self.client.post(
            self.verify_url,
            {'email': self.email, 'code': '012345'},
            format='json',
        )
        assert correct_response.status_code == status.HTTP_400_BAD_REQUEST
        assert PasswordResetChallenge.objects.get(user=self.user).attempts == self.max_attempts

    def test_new_request_replaces_the_previous_code(self):
        self.request_code(12345)
        challenge = PasswordResetChallenge.objects.get(user=self.user)

        with self.assertLogs('core.services.password_reset', level='WARNING') as captured_logs:
            cooldown_response = self.request_code(54321)
        assert cooldown_response.status_code == status.HTTP_202_ACCEPTED
        assert cooldown_response.data['detail'] == (
            'Se a conta existir, enviaremos as instruções para o e-mail cadastrado.'
        )
        assert len(mail.outbox) == 1
        assert 'reason=resend_cooldown' in captured_logs.output[0]

        challenge.created_at -= timedelta(minutes=2)
        challenge.save(update_fields=['created_at'])

        second_response = self.request_code(54321)

        assert second_response.status_code == status.HTTP_202_ACCEPTED
        assert len(mail.outbox) == self.expected_message_count_after_resend
        old_code_response = self.client.post(
            self.verify_url,
            {'email': self.email, 'code': '012345'},
            format='json',
        )
        new_code_response = self.client.post(
            self.verify_url,
            {'email': self.email, 'code': '054321'},
            format='json',
        )
        assert old_code_response.status_code == status.HTTP_400_BAD_REQUEST
        assert new_code_response.status_code == status.HTTP_200_OK

    def test_request_limits_apply_per_account(self):
        self.request_code()
        challenge = PasswordResetChallenge.objects.get(user=self.user)
        for code_number in (22222, 33333):
            challenge.created_at -= timedelta(minutes=2)
            challenge.save(update_fields=['created_at'])
            self.request_code(code_number)
            challenge.refresh_from_db()

        challenge.created_at -= timedelta(minutes=2)
        challenge.save(update_fields=['created_at'])
        assert len(mail.outbox) == self.max_requests_per_account
        assert PasswordResetChallenge.objects.get(user=self.user).requests_in_window == self.max_requests_per_account

        challenge = PasswordResetChallenge.objects.get(user=self.user)
        challenge.created_at -= timedelta(minutes=2)
        challenge.save(update_fields=['created_at'])
        with self.assertLogs('core.services.password_reset', level='WARNING') as captured_logs:
            self.request_code(44444)
        assert len(mail.outbox) == self.max_requests_per_account
        assert 'reason=request_limit' in captured_logs.output[0]

    def test_request_endpoint_is_throttled_per_ip(self):
        responses = [
            self.client.post(
                self.request_url,
                {'email': 'missing@example.com'},
                format='json',
            )
            for _ in range(self.max_requests_per_ip + 1)
        ]

        assert all(
            response.status_code == status.HTTP_202_ACCEPTED
            for response in responses[:self.max_requests_per_ip]
        )
        assert responses[-1].status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert int(responses[-1]['Retry-After']) > 0

    def test_confirm_changes_password_and_consumes_code(self):
        self.request_code()
        response = self.client.post(self.confirm_url, self.confirm_payload(), format='json')

        assert response.status_code == status.HTTP_200_OK
        self.user.refresh_from_db()
        challenge = PasswordResetChallenge.objects.get(user=self.user)
        assert self.user.check_password(self.new_password)
        assert challenge.used_at is not None
        reused_response = self.client.post(self.confirm_url, self.confirm_payload(), format='json')
        assert reused_response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_confirmation_must_match(self):
        response = self.client.post(
            self.confirm_url,
            self.confirm_payload(confirm_password='DifferentPassword!123'),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'confirm_password' in response.data

    def test_password_validators_are_enforced_after_code_validation(self):
        self.request_code()
        response = self.client.post(
            self.confirm_url,
            self.confirm_payload(new_password='password', confirm_password='password'),
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'new_password' in response.data
        self.user.refresh_from_db()
        assert self.user.check_password(self.initial_password)
        assert PasswordResetChallenge.objects.get(user=self.user).used_at is None

    def test_password_cannot_be_reset_without_a_valid_code(self):
        response = self.client.post(self.confirm_url, self.confirm_payload(), format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        self.user.refresh_from_db()
        assert self.user.check_password(self.initial_password)

    def test_login_works_only_with_the_new_password_after_reset(self):
        self.request_code()
        self.client.post(self.confirm_url, self.confirm_payload(), format='json')

        old_login = self.client.post(
            '/api/token/',
            {'email': self.email, 'password': self.initial_password},
            format='json',
        )
        new_login = self.client.post(
            '/api/token/',
            {'email': self.email, 'password': self.new_password},
            format='json',
        )

        assert old_login.status_code == status.HTTP_401_UNAUTHORIZED
        assert new_login.status_code == status.HTTP_200_OK

    def test_email_delivery_failure_is_logged_without_revealing_details(self):
        with self.assertLogs('core.services.password_reset', level='WARNING') as captured_logs:
            with patch(
                'core.services.password_reset.EmailMultiAlternatives.send',
                side_effect=smtplib.SMTPServerDisconnected('sensitive smtp detail'),
            ):
                response = self.request_code()

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert 'sensitive smtp detail' not in str(response.data)
        assert '012345' not in str(response.data)
        assert any(
            'stage=smtp account_id=' in message and 'exception=SMTPServerDisconnected' in message
            for message in captured_logs.output
        )
        assert not PasswordResetChallenge.objects.filter(user=self.user).exists()

    def test_template_rendering_failure_rolls_back_challenge(self):
        with (
            self.assertLogs('core.services.password_reset', level='ERROR') as captured_logs,
            patch(
                'core.services.password_reset.render_to_string',
                side_effect=TemplateDoesNotExist('missing-test-template.html'),
            ),
        ):
            response = self.request_code()

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert any(
            'stage=template account_id=' in message and 'exception=TemplateDoesNotExist' in message
            for message in captured_logs.output
        )
        assert not PasswordResetChallenge.objects.filter(user=self.user).exists()
