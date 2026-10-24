from rest_framework.permissions import SAFE_METHODS, BasePermission

from core.models import Projeto


def projetos_visiveis(user):
    return Projeto.objects.filter(participantes__usuario=user).distinct()


def participa(projeto, user):
    return projeto.participantes.filter(usuario=user).exists()


def administra(projeto, user):
    return projeto.participantes.filter(usuario=user, papel='admin').exists()


def edita_tarefa(tarefa, user):
    return participa(tarefa.projeto, user) and (administra(tarefa.projeto, user) or tarefa.responsavel_id == user.pk)


class ProjetoPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        projeto = obj if isinstance(obj, Projeto) else obj.projeto
        return participa(projeto, request.user) if request.method in SAFE_METHODS else administra(projeto, request.user)


class TarefaPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            participa(obj.projeto, request.user) if request.method in SAFE_METHODS else edita_tarefa(obj, request.user)
        )


class ChecklistPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        return (
            participa(obj.tarefa.projeto, request.user)
            if request.method in SAFE_METHODS
            else edita_tarefa(obj.tarefa, request.user)
        )


class ComentarioPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return participa(obj.tarefa.projeto, request.user)
        return edita_tarefa(obj.tarefa, request.user) and (
            obj.autor_id == request.user.pk or administra(obj.tarefa.projeto, request.user)
        )


class MaterialPermission(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return participa(obj.projeto, request.user)
        return participa(obj.projeto, request.user) and (
            obj.criador_id == request.user.pk or administra(obj.projeto, request.user)
        )
