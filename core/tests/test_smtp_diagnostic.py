import smtplib
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase, override_settings

from core.services.password_reset import _EmailDeliveryFailed, _send_reset_email


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend',
    EMAIL_HOST='smtp.gmail.com',
    EMAIL_PORT=587,
    EMAIL_HOST_USER='sender@example.com',
    EMAIL_HOST_PASSWORD='smtp-diagnostic-secret',
    EMAIL_USE_TLS=True,
    EMAIL_USE_SSL=False,
    DEFAULT_FROM_EMAIL='sender@example.com',
)
class SMTPDiagnosticCommandTests(SimpleTestCase):
    @patch('core.management.commands.diagnose_smtp.get_connection')
    def test_sends_only_to_the_explicit_recipient_and_does_not_print_secrets(self, get_connection):
        connection = get_connection.return_value
        connection.open.return_value = True
        connection.send_messages.return_value = 1
        output = StringIO()

        call_command(
            'diagnose_smtp',
            '--recipient',
            'authorized@example.net',
            stdout=output,
        )

        connection.open.assert_called_once_with()
        connection.send_messages.assert_called_once()
        diagnostic_message = connection.send_messages.call_args.args[0][0]
        assert diagnostic_message.to == ['authorized@example.net']
        assert diagnostic_message.from_email == 'sender@example.com'
        assert 'Tarefa de demonstração' in diagnostic_message.body
        assert 'Alex Demonstração' in diagnostic_message.body
        assert 'Quadro de demonstração' in diagnostic_message.body
        assert len(diagnostic_message.alternatives) == 1
        html_body = diagnostic_message.alternatives[0][0]
        assert diagnostic_message.alternatives[0][1] == 'text/html'
        assert '#1A3721' in html_body
        assert 'KANDO' in html_body
        assert 'Aceitar convite' in html_body
        assert 'Recusar convite' in html_body
        assert 'https://kando.example/convites/00000000-0000-0000-0000-000000000000/aceitar' in html_body
        assert 'https://kando.example/convites/00000000-0000-0000-0000-000000000000/recusar' in html_body
        assert 'kando.example' in diagnostic_message.body
        assert 'aceitou a mensagem' in output.getvalue()
        assert 'authorized@example.net' not in output.getvalue()
        assert 'smtp-diagnostic-secret' not in output.getvalue()
        connection.close.assert_called_once_with()

    @patch('core.management.commands.diagnose_smtp.get_connection')
    def test_send_test_email_command_accepts_positional_recipient(self, get_connection):
        connection = get_connection.return_value
        connection.open.return_value = True
        connection.send_messages.return_value = 1
        output = StringIO()

        call_command(
            'enviar_email_teste',
            'authorized@example.net',
            stdout=output,
        )

        connection.open.assert_called_once_with()
        connection.send_messages.assert_called_once()
        message = connection.send_messages.call_args.args[0][0]
        assert message.to == ['authorized@example.net']
        assert len(message.alternatives) == 1
        html_body = message.alternatives[0][0]
        assert '#1A3721' in html_body
        assert 'Aceitar convite' in html_body
        assert 'Recusar convite' in html_body
        assert 'smtp-diagnostic-secret' not in output.getvalue()


@override_settings(EMAIL_BACKEND='django.core.mail.backends.smtp.EmailBackend')
class PasswordResetSMTPStageTests(SimpleTestCase):
    def test_smtp_acceptance_is_logged_only_after_connection_and_submission(self):
        with (
            patch('core.services.password_reset.get_connection') as get_connection,
            patch(
                'core.services.password_reset.EmailMultiAlternatives.send',
                autospec=True,
                return_value=1,
            ) as send_email,
        ):
            smtp_connection = get_connection.return_value
            with self.assertLogs('core.services.password_reset', level='INFO') as captured_logs:
                _send_reset_email('registered@example.com', '012345', 7)

        smtp_connection.open.assert_called_once_with()
        smtp_connection.close.assert_called_once_with()
        assert send_email.call_args.args[0].connection is smtp_connection
        assert any('result=accepted_by_smtp' in log for log in captured_logs.output)

    def test_smtp_authentication_failure_is_distinguished_without_server_text(self):
        with patch('core.services.password_reset.get_connection') as get_connection:
            smtp_connection = get_connection.return_value
            smtp_connection.open.side_effect = smtplib.SMTPAuthenticationError(
                535,
                b'sensitive server response',
            )
            with (
                patch('core.services.password_reset.EmailMultiAlternatives.send') as send_email,
                self.assertLogs('core.services.password_reset', level='ERROR') as captured_logs,
            ):
                with self.assertRaises(_EmailDeliveryFailed):  # noqa: PT027
                    _send_reset_email('registered@example.com', '012345', 7)

        smtp_connection.close.assert_called_once_with()
        send_email.assert_not_called()
        assert any('stage=smtp_connection_or_authentication' in log for log in captured_logs.output)
        assert 'sensitive server response' not in str(captured_logs.output)

    def test_smtp_submission_rejection_is_distinguished(self):
        with patch('core.services.password_reset.get_connection') as get_connection:
            smtp_connection = get_connection.return_value
            smtp_connection.open.return_value = True
            with (
                patch(
                    'core.services.password_reset.EmailMultiAlternatives.send',
                    autospec=True,
                    return_value=0,
                ),
                self.assertLogs('core.services.password_reset', level='ERROR') as captured_logs,
            ):
                with self.assertRaises(_EmailDeliveryFailed):  # noqa: PT027
                    _send_reset_email('registered@example.com', '012345', 7)

        smtp_connection.close.assert_called_once_with()
        assert any('stage=smtp_submission result=not_accepted' in log for log in captured_logs.output)

    def test_recipient_refusal_logs_code_without_address_or_server_response(self):
        refused_address = 'private-recipient@example.net'
        private_response = b'private server response with recipient details'
        refusal = smtplib.SMTPRecipientsRefused({refused_address: (553, private_response)})

        with (
            patch('core.services.password_reset.get_connection') as get_connection,
            patch(
                'core.services.password_reset.EmailMultiAlternatives.send',
                autospec=True,
                side_effect=refusal,
            ),
            self.assertLogs('core.services.password_reset', level='ERROR') as captured_logs,
        ):
            get_connection.return_value.open.return_value = True
            with self.assertRaises(_EmailDeliveryFailed):  # noqa: PT027
                _send_reset_email(refused_address, '012345', 7)

        log_output = str(captured_logs.output)
        assert 'stage=smtp_submission' in log_output
        assert 'smtp_code=553' in log_output
        assert 'refused_recipient_count=1' in log_output
        assert refused_address not in log_output
        assert private_response.decode() not in log_output

    @patch('core.management.commands.diagnose_smtp.get_connection')
    def test_check_only_never_opens_an_smtp_connection(self, get_connection):
        output = StringIO()

        call_command('diagnose_smtp', '--check-only', stdout=output)

        get_connection.assert_not_called()
        assert 'nenhuma mensagem enviada' in output.getvalue()
        assert 'smtp-diagnostic-secret' not in output.getvalue()

    @patch('core.management.commands.diagnose_smtp.get_connection')
    def test_sender_mismatch_fails_before_connecting(self, get_connection):
        output = StringIO()

        with override_settings(DEFAULT_FROM_EMAIL='different@example.com'):
            with self.assertRaises(CommandError):  # noqa: PT027
                call_command('diagnose_smtp', '--check-only', stdout=output)

        get_connection.assert_not_called()
        assert 'remetente igual ao usuário SMTP' in output.getvalue()

    @patch('core.management.commands.diagnose_smtp.get_connection')
    def test_unaccepted_message_fails_and_closes_the_connection(self, get_connection):
        connection = get_connection.return_value
        connection.open.return_value = True
        connection.send_messages.return_value = 0

        with self.assertRaises(CommandError):  # noqa: PT027
            call_command('diagnose_smtp', '--recipient', 'authorized@example.net')

        connection.close.assert_called_once_with()
