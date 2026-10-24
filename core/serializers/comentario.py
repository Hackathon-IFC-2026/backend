from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from core.models import Comentario
from core.project_permissions import edita_tarefa


class ComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comentario
        fields = '__all__'
        read_only_fields = (
            'id',
            'autor',
        )

    def validate(self, attrs):
        parent = getattr(self.instance, 'tarefa') if self.instance else attrs['tarefa']
        if self.instance and attrs.get('tarefa', parent) != parent:
            raise serializers.ValidationError('Não é permitido transferir este registro.')
        if not edita_tarefa(parent, self.context['request'].user):
            raise PermissionDenied('Você não participa deste projeto.')
        return attrs
