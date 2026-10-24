from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from core.models import ParticipanteProjeto
from core.project_permissions import administra


class ParticipanteProjetoSerializer(serializers.ModelSerializer):
    capacidade = serializers.IntegerField(min_value=1, max_value=1000, required=False)
    class Meta:
        model = ParticipanteProjeto
        fields = '__all__'

    def validate(self, attrs):
        projeto = self.instance.projeto if self.instance else attrs['projeto']
        usuario = self.instance.usuario if self.instance else attrs['usuario']
        if not administra(projeto, self.context['request'].user):
            raise PermissionDenied('Somente administradores podem gerenciar participantes.')
        if self.instance and (attrs.get('projeto', projeto) != projeto or attrs.get('usuario', usuario) != usuario):
            raise serializers.ValidationError('Não é permitido transferir uma participação.')
        if not usuario.is_active:
            raise serializers.ValidationError({'usuario': 'A conta precisa estar ativa.'})
        return attrs
