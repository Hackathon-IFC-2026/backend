from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.serializers.task_drive import GoogleDriveFileSerializer
from core.services.google_drive import (
    GoogleDriveAuthorizationRequired,
    GoogleDriveNotConfigured,
    GoogleDriveProviderError,
    consume_authorization_state,
    create_authorization_url,
    exchange_authorization_code,
    list_drive_files,
)

MAX_PAGE_TOKEN_LENGTH = 2048


def _frontend_callback_url(result):
    base_url = settings.GOOGLE_DRIVE_FRONTEND_REDIRECT_URL
    split_url = urlsplit(base_url)
    query = dict(parse_qsl(split_url.query))
    query['google_drive'] = result
    return urlunsplit((split_url.scheme, split_url.netloc, split_url.path, urlencode(query), split_url.fragment))


class GoogleDriveAuthorizationView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            authorization_url = create_authorization_url(request.user)
        except GoogleDriveNotConfigured:
            return Response(
                {'detail': 'A integração com o Google Drive não está configurada.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response({'authorization_url': authorization_url}, status=status.HTTP_200_OK)


class GoogleDriveCallbackView(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()

    def get(self, request):
        state_user = consume_authorization_state(request.query_params.get('state'))
        if state_user is None:
            return Response({'detail': 'Estado OAuth inválido ou expirado.'}, status=status.HTTP_400_BAD_REQUEST)

        if request.query_params.get('error'):
            return self._redirect('denied')

        code = request.query_params.get('code')
        if not code:
            return Response(
                {'detail': 'O Google não retornou um código de autorização.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            exchange_authorization_code(state_user, code)
        except GoogleDriveNotConfigured:
            return self._redirect('configuration_error')
        except GoogleDriveProviderError:
            return self._redirect('authorization_error')
        return self._redirect('connected')

    @staticmethod
    def _redirect(result):
        return Response(status=status.HTTP_302_FOUND, headers={'Location': _frontend_callback_url(result)})


class GoogleDriveFileListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        page_token = request.query_params.get('page_token')
        if page_token is not None and len(page_token) > MAX_PAGE_TOKEN_LENGTH:
            return Response({'detail': 'O token de paginação é inválido.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            response = list_drive_files(request.user, page_token=page_token)
        except GoogleDriveAuthorizationRequired:
            return Response(
                {'detail': 'Conecte ou autorize novamente sua conta Google Drive.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        except GoogleDriveNotConfigured:
            return Response(
                {'detail': 'A integração com o Google Drive não está configurada.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except GoogleDriveProviderError:
            return Response(
                {'detail': 'Não foi possível consultar os arquivos do Google Drive. Tente novamente.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        files = GoogleDriveFileSerializer(data=response.get('files', []), many=True)
        if not files.is_valid():
            return Response(
                {'detail': 'O Google Drive retornou metadados inválidos.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(
            {
                'files': [
                    {
                        'id': file['id'],
                        'name': file['name'],
                        'mime_type': file['mimeType'],
                        'size': file.get('size'),
                        'web_view_link': file.get('webViewLink') or '',
                    }
                    for file in files.validated_data
                ],
                'next_page_token': response.get('nextPageToken'),
            },
            status=status.HTTP_200_OK,
        )
