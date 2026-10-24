from django.db import transaction
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.models import Task, TaskDriveAttachment
from core.serializers.task import TaskSerializer
from core.serializers.task_drive import (
    GoogleDriveFileSerializer,
    TaskDriveAttachmentSerializer,
    TaskDriveFileSelectionSerializer,
)
from core.services.google_drive import (
    GoogleDriveAuthorizationRequired,
    GoogleDriveFileUnavailable,
    GoogleDriveNotConfigured,
    GoogleDriveProviderError,
    get_drive_file_metadata,
)


def _google_drive_error_response(exc):
    if isinstance(exc, GoogleDriveAuthorizationRequired):
        detail = 'Conecte ou autorize novamente sua conta Google Drive.'
        response_status = status.HTTP_401_UNAUTHORIZED
    elif isinstance(exc, GoogleDriveNotConfigured):
        detail = 'A integração com o Google Drive não está configurada.'
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
    elif isinstance(exc, GoogleDriveFileUnavailable):
        detail = 'Um ou mais arquivos não existem ou não estão acessíveis pela conta autorizada.'
        response_status = status.HTTP_400_BAD_REQUEST
    else:
        detail = 'Não foi possível validar os arquivos no Google Drive. Tente novamente.'
        response_status = status.HTTP_502_BAD_GATEWAY
    return Response({'detail': detail}, status=response_status)


class TaskPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return request.user.pk in {obj.created_by_id, obj.board.owner_id} or (
                obj.participants.filter(pk=request.user.pk).exists()
            )
        return request.user.pk in {obj.created_by_id, obj.board.owner_id}


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = (permissions.IsAuthenticated, TaskPermissions)

    def get_queryset(self):
        return (
            Task.objects
            .filter(
                Q(created_by=self.request.user) | Q(board__owner=self.request.user) | Q(participants=self.request.user)
            )
            .distinct()
            .select_related('board', 'created_by', 'assignee')
            .prefetch_related('participants')
        )

    def perform_create(self, serializer):
        board = serializer.validated_data['board']
        if board.owner_id != self.request.user.pk:
            raise PermissionDenied('Somente o proprietário do quadro pode criar tarefas nele.')
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=('get', 'post'), url_path='drive-attachments')
    def drive_attachments(self, request, pk=None):
        task = self.get_object()
        if request.method == 'GET':
            attachments = task.drive_attachments.select_related('added_by')
            return Response(TaskDriveAttachmentSerializer(attachments, many=True).data)

        serializer = TaskDriveFileSelectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        file_ids = list(dict.fromkeys(serializer.validated_data['file_ids']))
        try:
            files = [get_drive_file_metadata(request.user, file_id) for file_id in file_ids]
        except (
            GoogleDriveAuthorizationRequired,
            GoogleDriveNotConfigured,
            GoogleDriveFileUnavailable,
            GoogleDriveProviderError,
        ) as exc:
            return _google_drive_error_response(exc)

        metadata_serializer = GoogleDriveFileSerializer(data=files, many=True)
        if not metadata_serializer.is_valid():
            return Response(
                {'detail': 'Não foi possível validar os metadados retornados pelo Google Drive.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        normalized_files = [
            {
                'id': file['id'],
                'name': file['name'],
                'mime_type': file['mimeType'],
                'size': file.get('size'),
                'web_view_link': file.get('webViewLink') or '',
            }
            for file in metadata_serializer.validated_data
        ]
        if any(file_metadata['id'] != file_id for file_id, file_metadata in zip(file_ids, normalized_files)):
            return Response(
                {'detail': 'O Google Drive retornou um arquivo diferente do solicitado.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        attachments = []
        with transaction.atomic():
            for file_metadata in normalized_files:
                attachment, created = TaskDriveAttachment.objects.get_or_create(
                    task=task,
                    drive_file_id=file_metadata['id'],
                    defaults={
                        'name': file_metadata['name'],
                        'mime_type': file_metadata['mime_type'],
                        'size': file_metadata.get('size'),
                        'web_view_link': file_metadata.get('web_view_link', ''),
                        'added_by': request.user,
                    },
                )
                if not created:
                    attachment.name = file_metadata['name']
                    attachment.mime_type = file_metadata['mime_type']
                    attachment.size = file_metadata.get('size')
                    attachment.web_view_link = file_metadata.get('web_view_link', '')
                    attachment.save(update_fields=('name', 'mime_type', 'size', 'web_view_link'))
                attachments.append(attachment)
        return Response(TaskDriveAttachmentSerializer(attachments, many=True).data)

    @action(
        detail=True,
        methods=('delete',),
        url_path='drive-attachments/(?P<attachment_id>[^/.]+)',
    )
    def remove_drive_attachment(self, request, pk=None, attachment_id=None):
        task = self.get_object()
        attachment = task.drive_attachments.filter(pk=attachment_id).first()
        if attachment is None:
            return Response({'detail': 'Anexo não encontrado.'}, status=status.HTTP_404_NOT_FOUND)
        attachment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
