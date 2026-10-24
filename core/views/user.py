from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import User
from core.serializers import UserRegistrationSerializer, UserSerializer


class UserViewSet(ModelViewSet):
    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    http_method_names = ['get', 'post', 'patch', 'put', 'delete', 'head', 'options']

    def create(self, request, *args, **kwargs):
        from rest_framework.exceptions import MethodNotAllowed

        raise MethodNotAllowed('POST')

    def perform_destroy(self, instance):
        from django.db import transaction
        from django.db.models.deletion import ProtectedError
        from rest_framework.exceptions import ValidationError

        from core.models import Projeto

        with transaction.atomic():
            projetos = Projeto.objects.select_for_update().filter(participantes__usuario=instance)
            for projeto in projetos:
                if (
                    projeto.participantes.filter(usuario=instance, papel='admin').exists()
                    and projeto.participantes.filter(papel='admin').count() <= 1
                ):
                    raise ValidationError('Defina outro administrador antes de excluir a conta.')
            try:
                instance.delete()
            except ProtectedError:
                raise ValidationError('Esta conta possui registros vinculados e não pode ser excluída.')

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            from core.serializers.user import UserDirectorySerializer

            return UserDirectorySerializer
        return UserSerializer

    def get_queryset(self):
        if self.request.method not in ['GET', 'HEAD', 'OPTIONS']:
            return User.objects.filter(pk=self.request.user.pk)
        qs = User.objects.filter(is_active=True).order_by('id')
        email = self.request.query_params.get('email')
        return qs.filter(email__iexact=email) if email else qs

    @extend_schema(
        summary='Dados do usuário autenticado',
        description='Retorna os dados do usuário autenticado.',
        responses={200: UserSerializer, 401: None},
    )
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Retorna os dados do usuário autenticado."""
        user = request.user
        serializer = UserSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='alterar-senha')
    def alterar_senha(self, request):
        from django.db import transaction

        from core.authentication import VersionedPairSerializer
        from core.serializers.user import AlterarSenhaSerializer

        serializer = AlterarSenhaSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            user = User.objects.select_for_update().get(pk=request.user.pk)
            if not user.check_password(serializer.validated_data['senha_atual']):
                from rest_framework.exceptions import ValidationError

                raise ValidationError({'senha_atual': 'Senha atual incorreta.'})
            user.set_password(serializer.validated_data['nova_senha'])
            user.token_version += 1
            user.save(update_fields=['password', 'token_version'])
            refresh = VersionedPairSerializer.get_token(user)
        return Response({'mensagem': 'Senha atualizada.', 'access': str(refresh.access_token), 'refresh': str(refresh)})


@extend_schema(
    summary='Registro de novo usuário',
    description='Cria um novo usuário no sistema. Não requer autenticação.',
    request=UserRegistrationSerializer,
    responses={201: UserRegistrationSerializer, 400: None},
)
class UserRegistrationView(CreateAPIView):
    """Endpoint para registro de novos usuários."""

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
