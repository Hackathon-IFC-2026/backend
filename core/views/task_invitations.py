from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from core.models import Task, TaskInvitation, User
from core.serializers.task_invitation import TaskInvitationCreateSerializer, TaskInvitationSerializer
from core.services.task_invitations import (
    INVITATION_LIFETIME,
    InvitationEmailError,
    respond_to_task_invitation,
    send_task_invitation_email,
)


class InvitationEmailUnavailable(APIException):
    status_code = status.HTTP_502_BAD_GATEWAY
    default_detail = 'Não foi possível enviar o convite. Tente novamente mais tarde.'
    default_code = 'invitation_email_unavailable'


class PendingInvitationExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = 'Já existe um convite pendente para esta tarefa.'
    default_code = 'pending_invitation_exists'


class TaskInvitationViewSet(viewsets.GenericViewSet):
    permission_classes = (IsAuthenticated,)
    serializer_class = TaskInvitationSerializer

    def get_queryset(self):
        return (
            TaskInvitation.objects
            .filter(invitee=self.request.user)
            .select_related('task', 'task__board', 'invited_by')
            .order_by('-created_at')
        )

    def list(self, request, *args, **kwargs):
        return self._list_response(request, self.get_queryset())

    @action(detail=False, methods=('get',), url_path='pending')
    def pending(self, request):
        invitations = self.get_queryset().filter(
            status=TaskInvitation.Status.PENDING,
            expires_at__gt=timezone.now(),
        )
        return self._list_response(request, invitations)

    def _list_response(self, request, invitations):
        page = self.paginate_queryset(invitations)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(invitations, many=True).data)

    def create(self, request, *args, **kwargs):
        serializer = TaskInvitationCreateSerializer(
            data=request.data,
            context={'request': request},
        )
        serializer.is_valid(raise_exception=True)
        try:
            invitation = self._create_and_send_invitation(serializer, request.user)
        except IntegrityError as exc:
            raise PendingInvitationExists from exc
        except InvitationEmailError as exc:
            raise InvitationEmailUnavailable from exc

        return Response(
            TaskInvitationSerializer(invitation).data,
            status=status.HTTP_201_CREATED,
        )

    def _create_and_send_invitation(self, serializer, inviter):
        task = serializer.validated_data['task']
        invitee = serializer.validated_data['invitee']
        now = timezone.now()
        with transaction.atomic():
            locked_task = Task.objects.select_for_update().select_related('board', 'created_by').get(pk=task.pk)
            if inviter.pk not in {locked_task.created_by_id, locked_task.board.owner_id}:
                raise PermissionDenied('Você não tem permissão para convidar pessoas para esta tarefa.')
            locked_invitee = User.objects.select_for_update().get(pk=invitee.pk, is_active=True)
            if locked_task.participants.filter(pk=locked_invitee.pk).exists():
                raise ValidationError('Este usuário já participa da tarefa.')
            existing = (
                TaskInvitation.objects
                .select_for_update()
                .filter(
                    task=locked_task,
                    invitee=locked_invitee,
                    status=TaskInvitation.Status.PENDING,
                )
                .first()
            )
            if existing is not None:
                if existing.expires_at > now:
                    raise PendingInvitationExists
                existing.status = TaskInvitation.Status.EXPIRED
                existing.save(update_fields=('status',))

            invitation = TaskInvitation.objects.create(
                task=locked_task,
                invitee=locked_invitee,
                invited_by=inviter,
                expires_at=now + INVITATION_LIFETIME,
            )
            send_task_invitation_email(invitation)
        return invitation

    @action(detail=True, methods=('post',), url_path='accept')
    def accept(self, request, pk=None):
        return self._respond(request, pk, TaskInvitation.Status.ACCEPTED)

    @action(detail=True, methods=('post',), url_path='decline')
    def decline(self, request, pk=None):
        return self._respond(request, pk, TaskInvitation.Status.DECLINED)

    def _respond(self, request, invitation_id, response_status):
        with transaction.atomic():
            invitation = self.get_queryset().select_for_update().filter(pk=invitation_id).first()
            if invitation is None:
                return Response({'detail': 'Convite não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
            result = respond_to_task_invitation(invitation, request.user, response_status)

        if result == 'expired':
            return Response({'detail': 'Este convite expirou.'}, status=status.HTTP_410_GONE)
        if result == 'already_responded':
            return Response({'detail': 'Este convite já foi respondido.'}, status=status.HTTP_409_CONFLICT)
        return Response(TaskInvitationSerializer(invitation).data, status=status.HTTP_200_OK)
