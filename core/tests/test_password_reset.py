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


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='kando.gerenciador@gmail.com',
    DEFAULT_FROM_EMAIL='kando.gerenciador@gmail.com',
)
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
    code_length = 6
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
        with self.assertLogs('core.services.password_reset', level='INFO') as captured_logs:
            response = self.request_code()

        assert response.status_code == status.HTTP_202_ACCEPTED
        assert response.data['detail'] == 'Se a conta existir, enviaremos as instruções para o e-mail cadastrado.'
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.subject == 'Recuperação de senha'
        assert message.from_email == 'kando.gerenciador@gmail.com'
        assert message.to == [self.email]
        assert '012345' in message.body.splitlines()
        assert 'Digite os seis dígitos exatamente como aparecem acima' in message.body
        assert '10 minutos' in message.body
        assert 'Kando' in message.body
        assert len(message.alternatives) == 1
        assert message.alternatives[0][1] == 'text/html'
        assert '012345' in message.alternatives[0][0]
        assert '<code' in message.alternatives[0][0]
        assert 'Selecione e copie os seis dígitos.' in message.alternatives[0][0]
        assert 'Kando' in message.alternatives[0][0]
        challenge = PasswordResetChallenge.objects.get(user=self.user)
        assert challenge.code_hash != '012345'
        assert len(challenge.code_hash) == self.sha256_digest_length
        assert any('stage=account result=eligible' in item for item in captured_logs.output)
        assert any('stage=message result=prepared' in item for item in captured_logs.output)
        assert any('result=accepted_by_backend' in item for item in captured_logs.output)
        assert all('flow_id=' in item for item in captured_logs.output)
        assert self.email not in str(captured_logs.output)
        assert '012345' not in str(captured_logs.output)

    def test_unknown_email_has_the_same_generic_response_without_sending(self):
        known_response = self.request_code()
        mail.outbox.clear()
        with self.assertLogs('core.services.password_reset', level='INFO') as captured_logs:
            unknown_response = self.client.post(
                self.request_url,
                {'email': 'missing@example.com'},
                format='json',
            )

        assert unknown_response.status_code == known_response.status_code
        assert unknown_response.data == known_response.data
        assert mail.outbox == []
        assert any(
            'stage=account result=unavailable reason=not_found' in item
            for item in captured_logs.output
        )

        inactive_email = 'inactive@example.net'
        User.objects.create_user(inactive_email, 'InactiveAccountPassword!123', is_active=False)
        with self.assertLogs('core.services.password_reset', level='INFO') as inactive_logs:
            inactive_response = self.client.post(
                self.request_url,
                {'email': inactive_email},
                format='json',
            )
        assert inactive_response.data == known_response.data
        assert mail.outbox == []
        assert any(
            'stage=account result=unavailable reason=inactive' in item
            for item in inactive_logs.output
        )

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

    def test_full_password_reset_flow_sends_code_verifies_resets_and_allows_login(self):
        self.request_code()
        assert len(mail.outbox) == 1
        message = mail.outbox[0]
        assert message.to == [self.email]
        code = next(
            line.strip()
            for line in message.body.splitlines()
            if len(line.strip()) == self.code_length and line.strip().isdigit()
        )

        verify_response = self.client.post(
            self.verify_url,
            {'email': self.email, 'code': code},
            format='json',
        )
        assert verify_response.status_code == status.HTTP_200_OK

        confirm_response = self.client.post(
            self.confirm_url,
            self.confirm_payload(code=code),
            format='json',
        )
        assert confirm_response.status_code == status.HTTP_200_OK

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
            'stage=email_backend result=failed' in message and 'exception=SMTPServerDisconnected' in message
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
            'stage=template result=failed reason=render_error exception=TemplateDoesNotExist' in message
            for message in captured_logs.output
        )
        assert not PasswordResetChallenge.objects.filter(user=self.user).exists()


class PasswordResetRequestValidationTests(APITestCase):
    def test_get_is_not_allowed_for_password_reset_request(self):
        response = self.client.get(
            '/api/auth/password-reset/request/',
            HTTP_HOST='127.0.0.1',
        )

        assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
        assert response['Allow'] == 'POST, OPTIONS'

    def test_missing_email_is_rejected_with_field_error(self):
        response = self.client.post(
            '/api/auth/password-reset/request/',
            {},
            format='json',
            HTTP_HOST='127.0.0.1',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data == {'email': ['Este campo é obrigatório.']}


@override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
class PasswordResetSMTPRequestTests(APITestCase):
    request_url = '/api/auth/password-reset/request/'
    email = 'smtp-request@example.com'

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(self.email, 'InitialPassword!123')

    def test_request_submits_recovery_message_to_registered_address_over_smtp(self):
        with (
            patch('core.services.password_reset.secrets.randbelow', return_value=12345),
            patch('core.services.password_reset.get_connection') as get_connection,
            patch(
                'core.services.password_reset.EmailMultiAlternatives.send',
                autospec=True,
                return_value=1,
            ) as send_email,
        ):
            smtp_connection = get_connection.return_value
            with self.assertLogs('core.services.password_reset', level='INFO') as captured_logs:
                response = self.client.post(self.request_url, {'email': self.email}, format='json')

        assert response.status_code == status.HTTP_202_ACCEPTED
        smtp_connection.open.assert_called_once_with()
        smtp_connection.close.assert_called_once_with()
        send_email.assert_called_once()
        message = send_email.call_args.args[0]
        assert message.to == [self.user.email]
        assert message.connection is smtp_connection
        assert any('stage=email_backend result=submission_started' in item for item in captured_logs.output)
        assert any('result=accepted_by_smtp' in item for item in captured_logs.output)
        assert '012345' not in str(captured_logs.output)
        assert self.user.email not in str(captured_logs.output)


class PasswordResetThrottleEnvironmentTests(APITestCase):
    local_repeat_count = 4
    endpoints_and_limits = (
        ('/api/auth/password-reset/request/', 10),
        ('/api/auth/password-reset/verify/', 20),
        ('/api/auth/password-reset/confirm/', 10),
    )

    def setUp(self):
        cache.clear()

    @override_settings(DEBUG=True, LOCAL_DEVELOPMENT=True)
    def test_local_development_opt_in_allows_repeated_requests_to_all_endpoints(self):
        for endpoint, rate_limit in self.endpoints_and_limits:
            cache.clear()
            responses = [
                self.client.post(
                    endpoint,
                    {},
                    format='json',
                    HTTP_HOST='127.0.0.1',
                )
                for _ in range(rate_limit + 1)
            ]

            assert all(response.status_code != status.HTTP_429_TOO_MANY_REQUESTS for response in responses)

    @override_settings(
        DEBUG=True,
        LOCAL_DEVELOPMENT=True,
        EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    )
    def test_local_loopback_allows_repeated_email_requests_without_account_cooldown(self):
        email = 'local-throttle-test@example.com'
        user = User.objects.create_user(email, 'InitialPassword!123')

        with patch(
            'core.services.password_reset.secrets.randbelow',
            side_effect=range(self.local_repeat_count),
        ):
            responses = [
                self.client.post(
                    '/api/auth/password-reset/request/',
                    {'email': email},
                    format='json',
                    REMOTE_ADDR='127.0.0.1',
                    HTTP_HOST='127.0.0.1',
                )
                for _ in range(self.local_repeat_count)
            ]

        assert all(response.status_code == status.HTTP_202_ACCEPTED for response in responses)
        assert len(mail.outbox) == self.local_repeat_count
        assert (
            PasswordResetChallenge.objects.get(user=user).requests_in_window
            == self.local_repeat_count
        )

    @override_settings(DEBUG=True, LOCAL_DEVELOPMENT=True)
    def test_local_opt_in_does_not_bypass_throttle_for_non_loopback_clients(self):
        for endpoint, rate_limit in self.endpoints_and_limits:
            cache.clear()
            responses = [
                self.client.post(
                    endpoint,
                    {},
                    format='json',
                    REMOTE_ADDR='192.0.2.1',
                    HTTP_HOST='127.0.0.1',
                )
                for _ in range(rate_limit + 1)
            ]

            assert all(
                response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
                for response in responses[:-1]
            )
            assert responses[-1].status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @override_settings(DEBUG=True, LOCAL_DEVELOPMENT=False)
    def test_debug_without_local_opt_in_keeps_throttle_active(self):
        for endpoint, rate_limit in self.endpoints_and_limits:
            cache.clear()
            responses = [
                self.client.post(endpoint, {}, format='json')
                for _ in range(rate_limit + 1)
            ]

            assert responses[-1].status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @override_settings(DEBUG=False, LOCAL_DEVELOPMENT=True)
    def test_production_debug_off_keeps_throttle_active_on_all_endpoints(self):
        for endpoint, rate_limit in self.endpoints_and_limits:
            cache.clear()
            responses = [
                self.client.post(endpoint, {}, format='json')
                for _ in range(rate_limit + 1)
            ]

            assert all(
                response.status_code != status.HTTP_429_TOO_MANY_REQUESTS
                for response in responses[:-1]
            )
            assert responses[-1].status_code == status.HTTP_429_TOO_MANY_REQUESTS
            assert int(responses[-1]['Retry-After']) > 0


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    EMAIL_HOST_USER='kando.gerenciador@gmail.com',
    DEFAULT_FROM_EMAIL='kando.gerenciador@gmail.com',
)
class PasswordResetMultipleAccountsTests(APITestCase):
    request_url = '/api/auth/password-reset/request/'
    expected_challenge_count_for_two_accounts = 2
    expected_challenge_count_for_two_accounts = 2

    def setUp(self):
        cache.clear()
        self.first_email = 'first-user@example.com'
        self.second_email = 'second-user@example.net'
        User.objects.create_user(self.first_email, 'FirstAccountPassword!123')
        User.objects.create_user(self.second_email, 'SecondAccountPassword!123')

    def test_each_account_receives_email_at_its_registered_address(self):
        first_response = self.client.post(
            self.request_url,
            {'email': self.first_email},
            format='json',
        )
        second_response = self.client.post(
            self.request_url,
            {'email': self.second_email},
            format='json',
        )

        assert first_response.status_code == status.HTTP_202_ACCEPTED
        assert second_response.status_code == status.HTTP_202_ACCEPTED
        assert [message.to for message in mail.outbox] == [
            [self.first_email],
            [self.second_email],
        ]
        assert [message.from_email for message in mail.outbox] == [
            'kando.gerenciador@gmail.com',
            'kando.gerenciador@gmail.com',
        ]
        assert (
            PasswordResetChallenge.objects.filter(
                user__email__in=[self.first_email, self.second_email]
            ).count()
            == self.expected_challenge_count_for_two_accounts
        )
