import hashlib
import json
import secrets
from datetime import timedelta
from http import HTTPStatus

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from oauthlib.oauth2.rfc6749.errors import OAuth2Error
from requests import RequestException

from core.models import GoogleDriveCredential, GoogleDriveOAuthState

DRIVE_SCOPES = ('https://www.googleapis.com/auth/drive.metadata.readonly',)
OAUTH_STATE_LIFETIME = timedelta(minutes=10)


class GoogleDriveNotConfigured(Exception):
    pass


class GoogleDriveAuthorizationRequired(Exception):
    pass


class GoogleDriveProviderError(Exception):
    pass


class GoogleDriveFileUnavailable(Exception):
    pass


def _oauth_client_config():
    client_id = settings.GOOGLE_DRIVE_CLIENT_ID
    client_secret = settings.GOOGLE_DRIVE_CLIENT_SECRET
    redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI
    if not all((client_id, client_secret, redirect_uri, settings.GOOGLE_DRIVE_FRONTEND_REDIRECT_URL)):
        raise GoogleDriveNotConfigured
    return {
        'web': {
            'client_id': client_id,
            'client_secret': client_secret,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': [redirect_uri],
        }
    }


def _fernet():
    key = settings.GOOGLE_DRIVE_TOKEN_ENCRYPTION_KEY
    if not key:
        raise GoogleDriveNotConfigured
    try:
        return Fernet(key.encode('ascii'))
    except (ValueError, UnicodeEncodeError) as exc:
        raise GoogleDriveNotConfigured from exc


def _encrypt_credentials(credentials):
    payload = credentials.to_json().encode('utf-8')
    return _fernet().encrypt(payload).decode('ascii')


def _decrypt_credentials(encrypted_credentials):
    try:
        payload = _fernet().decrypt(encrypted_credentials.encode('ascii'))
    except InvalidToken as exc:
        raise GoogleDriveNotConfigured from exc
    try:
        return Credentials.from_authorized_user_info(json.loads(payload), scopes=DRIVE_SCOPES)
    except (KeyError, TypeError, ValueError) as exc:
        raise GoogleDriveAuthorizationRequired from exc


def create_authorization_url(user):
    client_config = _oauth_client_config()
    _fernet()
    state = secrets.token_urlsafe(32)
    now = timezone.now()
    GoogleDriveOAuthState.objects.filter(expires_at__lte=now).delete()
    GoogleDriveOAuthState.objects.create(
        user=user,
        state_hash=hashlib.sha256(state.encode()).hexdigest(),
        expires_at=now + OAUTH_STATE_LIFETIME,
    )
    flow = Flow.from_client_config(client_config, scopes=DRIVE_SCOPES)
    flow.redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI
    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent',
        state=state,
    )
    return authorization_url


@transaction.atomic
def consume_authorization_state(state):
    if not state:
        return None
    state_hash = hashlib.sha256(state.encode()).hexdigest()
    oauth_state = (
        GoogleDriveOAuthState.objects
        .select_for_update()
        .filter(state_hash=state_hash, expires_at__gt=timezone.now())
        .first()
    )
    if oauth_state is None:
        return None
    user = oauth_state.user
    oauth_state.delete()
    return user


def exchange_authorization_code(user, code):
    flow = Flow.from_client_config(_oauth_client_config(), scopes=DRIVE_SCOPES)
    flow.redirect_uri = settings.GOOGLE_DRIVE_REDIRECT_URI
    try:
        flow.fetch_token(code=code)
    except (GoogleAuthError, OAuth2Error, RequestException, ValueError) as exc:
        raise GoogleDriveProviderError from exc

    credentials = flow.credentials
    existing = GoogleDriveCredential.objects.filter(user=user).first()
    if not credentials.refresh_token and existing:
        previous_credentials = _decrypt_credentials(existing.encrypted_credentials)
        credentials.refresh_token = previous_credentials.refresh_token
    if not credentials.refresh_token:
        raise GoogleDriveProviderError
    GoogleDriveCredential.objects.update_or_create(
        user=user,
        defaults={'encrypted_credentials': _encrypt_credentials(credentials)},
    )


def _get_credentials(user):
    credential_record = GoogleDriveCredential.objects.filter(user=user).first()
    if credential_record is None:
        raise GoogleDriveAuthorizationRequired
    credentials = _decrypt_credentials(credential_record.encrypted_credentials)
    if not credentials.refresh_token:
        raise GoogleDriveAuthorizationRequired
    if credentials.expired:
        try:
            credentials.refresh(Request())
        except (GoogleAuthError, RequestException) as exc:
            credential_record.delete()
            raise GoogleDriveAuthorizationRequired from exc
        credential_record.encrypted_credentials = _encrypt_credentials(credentials)
        credential_record.save(update_fields=('encrypted_credentials', 'updated_at'))
    return credentials


def _drive_service(user):
    credentials = _get_credentials(user)
    return build('drive', 'v3', credentials=credentials, cache_discovery=False)


def _handle_drive_http_error(exc, user):
    if exc.resp.status == HTTPStatus.UNAUTHORIZED:
        GoogleDriveCredential.objects.filter(user=user).delete()
        raise GoogleDriveAuthorizationRequired from exc
    raise GoogleDriveProviderError from exc


def list_drive_files(user, page_token=None):
    service = _drive_service(user)
    try:
        response = (
            service.files()
            .list(
                q='trashed = false',
                pageSize=100,
                pageToken=page_token,
                orderBy='name',
                fields='nextPageToken,files(id,name,mimeType,size,webViewLink)',
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
            )
            .execute()
        )
    except HttpError as exc:
        _handle_drive_http_error(exc, user)
    except (GoogleAuthError, RequestException) as exc:
        raise GoogleDriveProviderError from exc
    return response


def get_drive_file_metadata(user, file_id):
    service = _drive_service(user)
    try:
        return (
            service.files()
            .get(
                fileId=file_id,
                fields='id,name,mimeType,size,webViewLink',
                supportsAllDrives=True,
            )
            .execute()
        )
    except HttpError as exc:
        if exc.resp.status in {HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND}:
            raise GoogleDriveFileUnavailable from exc
        _handle_drive_http_error(exc, user)
    except (GoogleAuthError, RequestException) as exc:
        raise GoogleDriveProviderError from exc
