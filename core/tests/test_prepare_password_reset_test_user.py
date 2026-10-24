from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from core.models import User


class PreparePasswordResetTestUserCommandTests(TestCase):
    confirmation_prompt_count = 2

    @override_settings(DEBUG=True, LOCAL_DEVELOPMENT=True)
    def test_creates_active_non_privileged_account_without_echoing_email(self):
        output = StringIO()

        with patch(
            'core.management.commands.prepare_password_reset_test_user.getpass',
            side_effect=['controlled@example.com', 'controlled@example.com'],
        ) as getpass_mock:
            call_command('prepare_password_reset_test_user', stdout=output)

        user = User.objects.get(email='controlled@example.com')
        assert user.is_active
        assert not user.is_staff
        assert not user.is_superuser
        assert user.has_usable_password()
        assert user.email not in output.getvalue()
        assert getpass_mock.call_count == self.confirmation_prompt_count

    @override_settings(DEBUG=True, LOCAL_DEVELOPMENT=True)
    def test_does_not_activate_an_existing_inactive_account(self):
        user = User.objects.create_user(
            email='inactive@example.com',
            password='InitialPassword!123',
            is_active=False,
        )

        with (
            patch(
                'core.management.commands.prepare_password_reset_test_user.getpass',
                return_value='inactive@example.com',
            ),
            self.assertRaisesMessage(CommandError, 'está inativa'),
        ):
            call_command('prepare_password_reset_test_user', stdout=StringIO())

        user.refresh_from_db()
        assert not user.is_active

    @override_settings(DEBUG=False, LOCAL_DEVELOPMENT=True)
    def test_refuses_to_run_when_debug_is_disabled(self):
        with (
            patch('core.management.commands.prepare_password_reset_test_user.getpass') as getpass_mock,
            self.assertRaisesMessage(CommandError, 'só pode ser executado'),
        ):
            call_command('prepare_password_reset_test_user', stdout=StringIO())

        getpass_mock.assert_not_called()

    @override_settings(DEBUG=True, LOCAL_DEVELOPMENT=False)
    def test_refuses_to_run_without_local_development_opt_in(self):
        with (
            patch('core.management.commands.prepare_password_reset_test_user.getpass') as getpass_mock,
            self.assertRaisesMessage(CommandError, 'só pode ser executado'),
        ):
            call_command('prepare_password_reset_test_user', stdout=StringIO())

        getpass_mock.assert_not_called()
