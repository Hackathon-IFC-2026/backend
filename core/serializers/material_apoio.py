from rest_framework import serializers

from core.models import MaterialApoio


class MaterialApoioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialApoio
        fields = '__all__'
        read_only_fields = (
            'id',
            'criador',
            'criado_em',
        )

    def validate_projeto(self, projeto):
        usuario = self.context['request'].user

        participa = projeto.participantes.filter(
            usuario=usuario
        ).exists()

        if not participa:
            raise serializers.ValidationError(
                'Você precisa participar do projeto para adicionar materiais de apoio.'
            )

        return projeto

    def create(self, validated_data):
        validated_data['criador'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'projeto' in validated_data:
            if validated_data['projeto'] != instance.projeto:
                raise serializers.ValidationError({
                    'projeto': 'Não é permitido transferir o material para outro projeto.'
                })

        return super().update(instance, validated_data)