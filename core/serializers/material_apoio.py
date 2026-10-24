from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from core.models import MaterialApoio
from core.project_permissions import participa


class MaterialApoioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialApoio
        fields = '__all__'
        read_only_fields = (
            'id',
            'criador',
        )

    def validate(self, attrs):
        parent = getattr(self.instance, 'projeto') if self.instance else attrs['projeto']
        if self.instance and attrs.get('projeto', parent) != parent:
            raise serializers.ValidationError('Não é permitido transferir este registro.')
        projeto = parent
        if not participa(projeto, self.context['request'].user):
            raise PermissionDenied('Você não participa deste projeto.')
        return attrs
