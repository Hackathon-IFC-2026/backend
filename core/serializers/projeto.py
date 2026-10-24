from rest_framework import serializers

from core.models import Projeto


class ProjetoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projeto
        fields = '__all__'
        read_only_fields = ('id', 'criado_em', 'atualizado_em', 'criado_por')

    def create(self, validated_data):
        validated_data['criado_por'] = self.context['request'].user
        return super().create(validated_data)
