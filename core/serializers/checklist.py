from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from core.models import Checklist
from core.project_permissions import edita_tarefa, participa


class ChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checklist
        fields = '__all__'
        read_only_fields = ('id',)

    def validate(self, attrs):
        parent = getattr(self.instance, 'tarefa') if self.instance else attrs['tarefa']
        if self.instance and attrs.get('tarefa', parent) != parent:
            raise serializers.ValidationError('Não é permitido transferir este registro.')
        projeto = parent.projeto
        if not participa(projeto, self.context['request'].user):
            raise PermissionDenied('Você não participa deste projeto.')
        if not edita_tarefa(parent, self.context['request'].user):
            raise PermissionDenied('Você não pode modificar esta tarefa.')
        return attrs
