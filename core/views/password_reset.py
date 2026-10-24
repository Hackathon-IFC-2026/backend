import ipaddress
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ValidationError as PasswordValidationError
from drf_spectacular.utils import extend_schema
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from core.serializers import (
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetVerifySerializer,
)
from core.services.password_reset import (
    request_password_reset,
    reset_password,
    verify_password_reset_code,
)

GENERIC_REQUEST_DETAIL = 'Se a conta existir, enviaremos as instruções para o e-mail cadastrado.'
INVALID_CODE_DETAIL = 'Código inválido ou expirado.'


class PasswordResetScopedRateThrottle(ScopedRateThrottle):
    @staticmethod
    def is_local_development_request(request):
        if not (settings.DEBUG and settings.LOCAL_DEVELOPMENT):
            return False

        try:
            remote_is_loopback = ipaddress.ip_address(request.META.get('REMOTE_ADDR', '')).is_loopback
            hostname = urlsplit(f'//{request.get_host()}').hostname
            host_is_loopback = hostname == 'localhost' or ipaddress.ip_address(hostname).is_loopback
            return remote_is_loopback and host_is_loopback
        except (TypeError, ValueError):
            return False

    def allow_request(self, request, view):
        if self.is_local_development_request(request):
            return True
        return super().allow_request(request, view)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetScopedRateThrottle]
    throttle_scope = 'password_reset_request'

    @extend_schema(
        summary='Solicitar recuperação de senha',
        request=PasswordResetRequestSerializer,
        responses={202: None, 400: None, 429: None},
    )
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request_password_reset(
            serializer.validated_data['email'],
            allow_repeated_requests=PasswordResetScopedRateThrottle.is_local_development_request(request),
        )
        return Response({'detail': GENERIC_REQUEST_DETAIL}, status=status.HTTP_202_ACCEPTED)


class PasswordResetVerifyView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetScopedRateThrottle]
    throttle_scope = 'password_reset_verify'

    @extend_schema(
        summary='Validar código de recuperação',
        request=PasswordResetVerifySerializer,
        responses={200: None, 400: None, 429: None},
    )
    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if not verify_password_reset_code(**serializer.validated_data):
            return Response({'detail': INVALID_CODE_DETAIL}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Código válido.'}, status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [PasswordResetScopedRateThrottle]
    throttle_scope = 'password_reset_confirm'

    @extend_schema(
        summary='Redefinir senha',
        request=PasswordResetConfirmSerializer,
        responses={200: None, 400: None, 429: None},
    )
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            password_was_reset = reset_password(
                email=serializer.validated_data['email'],
                code=serializer.validated_data['code'],
                new_password=serializer.validated_data['new_password'],
            )
        except PasswordValidationError as exc:
            raise serializers.ValidationError({'new_password': exc.messages}) from exc

        if not password_was_reset:
            return Response({'detail': INVALID_CODE_DETAIL}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'detail': 'Senha redefinida com sucesso.'}, status=status.HTTP_200_OK)
