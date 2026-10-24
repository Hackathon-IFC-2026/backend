import json
from datetime import timedelta
from unittest.mock import Mock, call, patch
from urllib.parse import parse_qs, urlsplit

from cryptography.fernet import Fernet
from django.test import override_settings
from django.utils import timezone
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    Board,
    GoogleDriveCredential,
    GoogleDriveOAuthState,
    Task,
    TaskDriveAttachment,
    User,
)
from core.services import google_drive

TEST_ENCRYPTION_KEY = Fernet.generate_key().decode()
FILE_SIZE_BYTES = 1234
GOOGLE_SETTINGS = {
    'GOOGLE_DRIVE_CLIENT_ID': 'test-client-id',
    'GOOGLE_DRIVE_CLIENT_SECRET': 'test-client-secret',
    'GOOGLE_DRIVE_REDIRECT_URI': 'https://api.example.test/api/google-drive/callback/',
    'GOOGLE_DRIVE_FRONTEND_REDIRECT_URL': 'https://frontend.example.test/tasks',
    'GOOGLE_DRIVE_TOKEN_ENCRYPTION_KEY': TEST_ENCRYPTION_KEY,
}


@override_settings(**GOOGLE_SETTINGS)
class GoogleDriveAPITests(APITestCase):
    authorization_url = '/api/google-drive/authorization/'
    callback_url = '/api/google-drive/callback/'
    files_url = '/api/google-drive/files/'
    task_attachments_url = '/api/tasks/{}/drive-attachments/'

    def setUp(self):
        self.owner = User.objects.create_user('owner@example.com', 'OwnerPassword!123')
        self.participant = User.objects.create_user('participant@example.com', 'ParticipantPassword!123')
        self.outsider = User.objects.create_user('outsider@example.com', 'OutsiderPassword!123')
        self.board = Board.objects.create(owner=self.owner, title='Project')
        self.task = Task.objects.create(board=self.board, title='Review', created_by=self.owner)
        self.task.participants.add(self.participant)

    def test_google_drive_endpoints_require_authentication(self):
        assert self.client.post(self.authorization_url).status_code == status.HTTP_401_UNAUTHORIZED
        assert self.client.get(self.files_url).status_code == status.HTTP_401_UNAUTHORIZED
        assert self.client.post(
            self.task_attachments_url.format(self.task.pk),
            {'file_ids': ['drive-file']},
            format='json',
        ).status_code == status.HTTP_401_UNAUTHORIZED

    def test_authorization_start_returns_google_url_and_persists_only_state_hash(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(self.authorization_url)

        assert response.status_code == status.HTTP_200_OK
        assert set(response.data) == {'authorization_url'}
        query = parse_qs(urlsplit(response.data['authorization_url']).query)
        assert query['scope'] == [google_drive.DRIVE_SCOPES[0]]
        assert query['access_type'] == ['offline']
        assert query['state'][0]
        oauth_state = GoogleDriveOAuthState.objects.get(user=self.owner)
        assert oauth_state.state_hash != query['state'][0]
        assert oauth_state.expires_at > timezone.now()

    @override_settings(GOOGLE_DRIVE_CLIENT_ID='')
    def test_authorization_start_reports_missing_configuration(self):
        self.client.force_authenticate(self.owner)

        response = self.client.post(self.authorization_url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch('core.views.google_drive.exchange_authorization_code')
    def test_callback_consumes_state_and_never_returns_oauth_tokens(self, exchange):
        self.client.force_authenticate(self.owner)
        authorization = self.client.post(self.authorization_url)
        state = parse_qs(urlsplit(authorization.data['authorization_url']).query)['state'][0]

        response = self.client.get(self.callback_url, {'state': state, 'code': 'one-time-code'})

        assert response.status_code == status.HTTP_302_FOUND
        assert response['Location'] == 'https://frontend.example.test/tasks?google_drive=connected'
        assert GoogleDriveOAuthState.objects.count() == 0
        exchange.assert_called_once_with(self.owner, 'one-time-code')
        assert 'token' not in response.content.decode().lower()

    @patch('core.views.google_drive.exchange_authorization_code')
    def test_callback_does_not_exchange_an_invalid_or_replayed_state(self, exchange):
        response = self.client.get(self.callback_url, {'state': 'invalid', 'code': 'code'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        exchange.assert_not_called()

    @patch('core.views.google_drive.exchange_authorization_code')
    def test_callback_rejects_expired_state(self, exchange):
        self.client.force_authenticate(self.owner)
        authorization = self.client.post(self.authorization_url)
        state = parse_qs(urlsplit(authorization.data['authorization_url']).query)['state'][0]
        oauth_state = GoogleDriveOAuthState.objects.get(user=self.owner)
        oauth_state.expires_at = timezone.now() - timedelta(seconds=1)
        oauth_state.save(update_fields=('expires_at',))

        response = self.client.get(self.callback_url, {'state': state, 'code': 'code'})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        exchange.assert_not_called()

    def test_callback_reports_google_consent_denial_without_exposing_details(self):
        self.client.force_authenticate(self.owner)
        authorization = self.client.post(self.authorization_url)
        state = parse_qs(urlsplit(authorization.data['authorization_url']).query)['state'][0]

        response = self.client.get(
            self.callback_url,
            {'state': state, 'error': 'access_denied', 'error_description': 'private provider response'},
        )

        assert response.status_code == status.HTTP_302_FOUND
        assert response['Location'].endswith('?google_drive=denied')
        assert 'private' not in response['Location']

    @patch('core.views.google_drive.list_drive_files')
    def test_authenticated_user_can_list_files_with_metadata(self, list_files):
        self.client.force_authenticate(self.owner)
        list_files.return_value = {
            'files': [
                {
                    'id': 'file-id',
                    'name': 'Plan.pdf',
                    'mimeType': 'application/pdf',
                    'size': str(FILE_SIZE_BYTES),
                    'webViewLink': 'https://drive.google.com/file/d/file-id/view',
                }
            ],
            'nextPageToken': 'next-page',
        }

        response = self.client.get(self.files_url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data == {
            'files': [
                {
                    'id': 'file-id',
                    'name': 'Plan.pdf',
                    'mime_type': 'application/pdf',
                    'size': 1234,
                    'web_view_link': 'https://drive.google.com/file/d/file-id/view',
                }
            ],
            'next_page_token': 'next-page',
        }
        list_files.assert_called_once_with(self.owner, page_token=None)

    @patch(
        'core.views.google_drive.list_drive_files',
        side_effect=google_drive.GoogleDriveAuthorizationRequired(),
    )
    def test_file_listing_requires_a_valid_google_authorization(self, list_files):
        self.client.force_authenticate(self.owner)

        response = self.client.get(self.files_url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        list_files.assert_called_once()

    @patch(
        'core.views.google_drive.list_drive_files',
        side_effect=google_drive.GoogleDriveProviderError(),
    )
    def test_google_api_failure_during_listing_is_reported_as_gateway_error(self, list_files):
        self.client.force_authenticate(self.owner)

        response = self.client.get(self.files_url)

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        list_files.assert_called_once()

    @patch('core.views.tasks.get_drive_file_metadata')
    def test_owner_can_associate_verified_files_without_duplicate_task_or_attachment(self, get_file):
        get_file.return_value = {
            'id': 'file-id',
            'name': 'Plan.pdf',
            'mimeType': 'application/pdf',
            'size': str(FILE_SIZE_BYTES),
            'webViewLink': 'https://drive.google.com/file/d/file-id/view',
        }
        self.client.force_authenticate(self.owner)
        task_count = Task.objects.count()
        payload = {'file_ids': ['file-id', 'file-id']}

        first_response = self.client.post(
            self.task_attachments_url.format(self.task.pk),
            payload,
            format='json',
        )
        second_response = self.client.post(
            self.task_attachments_url.format(self.task.pk),
            payload,
            format='json',
        )

        assert first_response.status_code == status.HTTP_200_OK
        assert second_response.status_code == status.HTTP_200_OK
        assert first_response.data == second_response.data
        assert Task.objects.count() == task_count
        assert TaskDriveAttachment.objects.filter(task=self.task, drive_file_id='file-id').count() == 1
        assert get_file.call_args_list == [
            call(self.owner, 'file-id'),
            call(self.owner, 'file-id'),
        ]
        attachment = TaskDriveAttachment.objects.get()
        assert attachment.added_by == self.owner
        assert attachment.size == FILE_SIZE_BYTES

    @patch(
        'core.views.tasks.get_drive_file_metadata',
        side_effect=google_drive.GoogleDriveFileUnavailable(),
    )
    def test_inaccessible_file_is_rejected_without_creating_an_association(self, get_file):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            self.task_attachments_url.format(self.task.pk),
            {'file_ids': ['missing-file']},
            format='json',
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert not TaskDriveAttachment.objects.exists()
        get_file.assert_called_once_with(self.owner, 'missing-file')

    @patch(
        'core.views.tasks.get_drive_file_metadata',
        side_effect=google_drive.GoogleDriveProviderError(),
    )
    def test_google_api_error_during_association_is_reported(self, get_file):
        self.client.force_authenticate(self.owner)

        response = self.client.post(
            self.task_attachments_url.format(self.task.pk),
            {'file_ids': ['file-id']},
            format='json',
        )

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert not TaskDriveAttachment.objects.exists()
        get_file.assert_called_once_with(self.owner, 'file-id')

    @patch('core.views.tasks.get_drive_file_metadata')
    def test_users_without_task_write_permission_cannot_associate_files(self, get_file):
        self.client.force_authenticate(self.participant)

        response = self.client.post(
            self.task_attachments_url.format(self.task.pk),
            {'file_ids': ['file-id']},
            format='json',
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        get_file.assert_not_called()
        assert not TaskDriveAttachment.objects.exists()

    def test_task_participants_can_read_associations_but_outsiders_cannot(self):
        attachment = TaskDriveAttachment.objects.create(
            task=self.task,
            drive_file_id='file-id',
            name='Plan.pdf',
            mime_type='application/pdf',
        )
        self.client.force_authenticate(self.participant)

        response = self.client.get(self.task_attachments_url.format(self.task.pk))

        assert response.status_code == status.HTTP_200_OK
        assert response.data[0]['id'] == attachment.pk
        self.client.force_authenticate(self.outsider)
        assert self.client.get(self.task_attachments_url.format(self.task.pk)).status_code == status.HTTP_404_NOT_FOUND

    def test_task_owner_can_remove_association_without_deleting_google_file(self):
        attachment = TaskDriveAttachment.objects.create(
            task=self.task,
            drive_file_id='file-id',
            name='Plan.pdf',
            mime_type='application/pdf',
        )
        self.client.force_authenticate(self.owner)

        response = self.client.delete(
            f'{self.task_attachments_url.format(self.task.pk)}{attachment.pk}/',
        )

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not TaskDriveAttachment.objects.exists()


@override_settings(**GOOGLE_SETTINGS)
class GoogleDriveCredentialServiceTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user('drive-user@example.com', 'DrivePassword!123')
        encrypted = Fernet(TEST_ENCRYPTION_KEY.encode()).encrypt(b'{}').decode()
        self.record = GoogleDriveCredential.objects.create(
            user=self.user,
            encrypted_credentials=encrypted,
        )
        self.original_encrypted_credentials = self.record.encrypted_credentials

    @patch('core.services.google_drive.Flow.from_client_config')
    def test_authorization_code_exchange_encrypts_tokens_before_persisting(self, from_client_config):
        flow = Mock()
        flow.credentials.refresh_token = 'private-refresh-token'
        flow.credentials.to_json.return_value = json.dumps(
            {
                'token': 'private-access-token',
                'refresh_token': 'private-refresh-token',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': GOOGLE_SETTINGS['GOOGLE_DRIVE_CLIENT_ID'],
                'client_secret': GOOGLE_SETTINGS['GOOGLE_DRIVE_CLIENT_SECRET'],
                'scopes': list(google_drive.DRIVE_SCOPES),
            }
        )
        from_client_config.return_value = flow

        google_drive.exchange_authorization_code(self.user, 'authorization-code')

        flow.fetch_token.assert_called_once_with(code='authorization-code')
        stored = GoogleDriveCredential.objects.get(user=self.user).encrypted_credentials
        assert 'private-access-token' not in stored
        assert 'private-refresh-token' not in stored
        decrypted = Fernet(TEST_ENCRYPTION_KEY.encode()).decrypt(stored.encode()).decode()
        assert 'private-access-token' in decrypted
        assert 'private-refresh-token' in decrypted

    @patch('core.services.google_drive.Credentials.from_authorized_user_info')
    def test_expired_tokens_are_refreshed_and_encrypted_back_to_database(self, from_authorized_user_info):
        credentials = Mock(expired=True, refresh_token='refresh-token')
        credentials.to_json.return_value = '{"token":"refreshed"}'
        from_authorized_user_info.return_value = credentials

        result = google_drive._get_credentials(self.user)

        assert result is credentials
        credentials.refresh.assert_called_once()
        self.record.refresh_from_db()
        assert self.record.encrypted_credentials != self.original_encrypted_credentials

    @patch('core.services.google_drive.Credentials.from_authorized_user_info')
    def test_revoked_refresh_token_requires_reauthorization_and_is_removed(self, from_authorized_user_info):
        credentials = Mock(expired=True, refresh_token='revoked-refresh-token')
        credentials.refresh.side_effect = RefreshError('private token error')
        from_authorized_user_info.return_value = credentials

        with self.assertRaises(google_drive.GoogleDriveAuthorizationRequired):  # noqa: PT027
            google_drive._get_credentials(self.user)

        assert not GoogleDriveCredential.objects.filter(user=self.user).exists()

    @patch('core.services.google_drive._drive_service')
    def test_google_reports_missing_or_inaccessible_file(self, drive_service):
        response = Mock(status=404)
        execute = drive_service.return_value.files.return_value.get.return_value.execute
        execute.side_effect = HttpError(response, b'private Google response')

        with self.assertRaises(google_drive.GoogleDriveFileUnavailable):  # noqa: PT027
            google_drive.get_drive_file_metadata(self.user, 'missing-file')

    @patch('core.services.google_drive._drive_service')
    def test_google_api_server_error_is_mapped_to_provider_error(self, drive_service):
        response = Mock(status=500)
        execute = drive_service.return_value.files.return_value.list.return_value.execute
        execute.side_effect = HttpError(response, b'private Google response')

        with self.assertRaises(google_drive.GoogleDriveProviderError):  # noqa: PT027
            google_drive.list_drive_files(self.user)

    @patch('core.services.google_drive._drive_service')
    def test_google_api_authentication_failure_removes_credential(self, drive_service):
        response = Mock(status=401)
        execute = drive_service.return_value.files.return_value.list.return_value.execute
        execute.side_effect = HttpError(response, b'private Google response')

        with self.assertRaises(google_drive.GoogleDriveAuthorizationRequired):  # noqa: PT027
            google_drive.list_drive_files(self.user)

        assert not GoogleDriveCredential.objects.filter(user=self.user).exists()
