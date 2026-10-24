from django.db import transaction
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from core.models import Projeto
from core.project_permissions import ProjetoPermission, administra, projetos_visiveis
from core.serializers import ProjetoSerializer


class ProjetoViewSet(ModelViewSet):
    queryset = Projeto.objects.none()
    serializer_class = ProjetoSerializer
    permission_classes = [IsAuthenticated, ProjetoPermission]

    def get_queryset(self):
        return projetos_visiveis(self.request.user).select_related('criado_por').order_by('criado_em', 'id')

    @transaction.atomic
    def perform_update(self, serializer):
        projeto = Projeto.objects.select_for_update().get(pk=serializer.instance.pk)
        if not administra(projeto, self.request.user):
            raise PermissionDenied('Somente administradores podem editar o projeto.')
        serializer.instance = projeto
        serializer.save()

    @transaction.atomic
    def perform_destroy(self, instance):
        projeto = Projeto.objects.select_for_update().get(pk=instance.pk)
        if not administra(projeto, self.request.user):
            raise PermissionDenied('Somente administradores podem excluir o projeto.')
        projeto.delete()
