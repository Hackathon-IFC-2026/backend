from rest_framework import serializers

from core.models import Projeto, ParticipanteProjeto


class ProjetoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projeto
        fields = '__all__'
        read_only_fields = (
            'id',
            'criado_por',
            'criado_em',
            'atualizado_em',
        )

    def create(self, validated_data):
        usuario = self.context['request'].user

        projeto = Projeto.objects.create(
            criado_por=usuario,
            **validated_data
        )

        ParticipanteProjeto.objects.create(
            projeto=projeto,
            usuario=usuario,
            papel=ParticipanteProjeto.Papel.ADMIN,
        )

        return projeto

    def validate(self, attrs):
        if self.instance is not None and 'criado_por' in attrs:
            raise serializers.ValidationError({
                'criado_por': 'Não é permitido alterar o criador do projeto.'
            })

        return attrs