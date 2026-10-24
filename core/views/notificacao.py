from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from core.models import Notificacao
from core.services.notificacoes import prazos


class NotificacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notificacao
        fields = ['id', 'projeto', 'tarefa', 'tipo', 'titulo', 'mensagem', 'lida', 'criada_em']
        read_only_fields = ['id', 'projeto', 'tarefa', 'tipo', 'titulo', 'mensagem', 'criada_em']


class NotificacaoViewSet(ModelViewSet):
    serializer_class = NotificacaoSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'patch', 'delete', 'head', 'options', 'post']

    def get_queryset(self):
        return Notificacao.objects.filter(usuario=self.request.user, excluida=False)

    def list(self, request, *args, **kwargs):
        prazos(request.user)
        return super().list(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.excluida = True
        instance.save(update_fields=['excluida'])

    def create(self, request, *args, **kwargs):
        from rest_framework.exceptions import MethodNotAllowed

        raise MethodNotAllowed('POST')

    @action(detail=False, methods=['post'], url_path='ler-todas')
    def ler_todas(self, request):
        total = self.get_queryset().filter(lida=False).update(lida=True)
        return Response({'atualizadas': total})
