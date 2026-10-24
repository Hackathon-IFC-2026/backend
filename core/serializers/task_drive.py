from rest_framework import serializers

from core.models import TaskDriveAttachment


class TaskDriveFileSelectionSerializer(serializers.Serializer):
    file_ids = serializers.ListField(
        child=serializers.CharField(max_length=255, allow_blank=False, trim_whitespace=True),
        allow_empty=False,
        max_length=50,
    )


class TaskDriveAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskDriveAttachment
        fields = (
            'id',
            'drive_file_id',
            'name',
            'mime_type',
            'size',
            'web_view_link',
            'added_by',
            'created_at',
        )
        read_only_fields = fields


class GoogleDriveFileSerializer(serializers.Serializer):
    id = serializers.CharField(max_length=255)
    name = serializers.CharField(max_length=1024)
    mimeType = serializers.CharField(max_length=255)
    size = serializers.IntegerField(required=False, allow_null=True)
    webViewLink = serializers.URLField(required=False, allow_blank=True, allow_null=True, max_length=200)
