from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from core.models import User


def conferir(user, token):
    if not user or not user.is_active or token.get('version', 0) != user.token_version:
        raise AuthenticationFailed('Sessão expirada. Entre novamente.')


class VersionedJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        conferir(user, validated_token)
        return user


class VersionedPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['version'] = user.token_version
        return token


class VersionedRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        token = RefreshToken(attrs['refresh'])
        user = User.objects.filter(pk=token['user_id']).first()
        conferir(user, token)
        return super().validate(attrs)
