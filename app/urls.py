from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)
from rest_framework.routers import DefaultRouter

from core.views import (
    BoardViewSet,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CustomTokenVerifyView,
    GoogleDriveAuthorizationView,
    GoogleDriveCallbackView,
    GoogleDriveFileListView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetVerifyView,
    TaskInvitationViewSet,
    TaskViewSet,
    UserRegistrationView,
    UserViewSet,
    ValidacaoViewSet,
)

router = DefaultRouter()
router.register(r'usuarios', UserViewSet, basename='usuarios')
router.register(r'validacoes', ValidacaoViewSet, basename='validacoes')
router.register(r'boards', BoardViewSet, basename='board')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'invitations', TaskInvitationViewSet, basename='task-invitation')


urlpatterns = [
    path('admin/', admin.site.urls),
    # OpenAPI 3
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path(
        'api/doc/',
        SpectacularSwaggerView.as_view(url_name='schema'),
        name='swagger-ui',
    ),
    path(
        'api/redoc/',
        SpectacularRedocView.as_view(url_name='schema'),
        name='redoc',
    ),
    # Autenticação JWT
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', CustomTokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', CustomTokenVerifyView.as_view(), name='token_verify'),
    # Registro de usuários
    path('api/registro/', UserRegistrationView.as_view(), name='user_registration'),
    path(
        'api/auth/password-reset/request/',
        PasswordResetRequestView.as_view(),
        name='password_reset_request',
    ),
    path(
        'api/auth/password-reset/verify/',
        PasswordResetVerifyView.as_view(),
        name='password_reset_verify',
    ),
    path(
        'api/auth/password-reset/confirm/',
        PasswordResetConfirmView.as_view(),
        name='password_reset_confirm',
    ),
    path(
        'api/google-drive/authorization/',
        GoogleDriveAuthorizationView.as_view(),
        name='google_drive_authorization',
    ),
    path('api/google-drive/callback/', GoogleDriveCallbackView.as_view(), name='google_drive_callback'),
    path('api/google-drive/files/', GoogleDriveFileListView.as_view(), name='google_drive_files'),
    # API
    path('api/', include(router.urls)),
]
