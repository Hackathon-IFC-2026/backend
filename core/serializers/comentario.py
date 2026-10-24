from rest_framework import serializers

from core.models import Comentario


class ComentarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comentario
        fields = '__all__'
        read_only_fields = (
            'id',
            'autor',
            'criado_em',
        )

    def validate_tarefa(self, tarefa):
        usuario = self.context['request'].user

        participa = tarefa.projeto.participantes.filter(
            usuario=usuario
        ).exists()

        if not participa:
            raise serializers.ValidationError(
                'Você precisa participar do projeto para comentar nesta tarefa.'
            )

        return tarefa

    def validate(self, attrs):
        # Na edição, não permitimos trocar a tarefa do comentário.
        if self.instance is not None and 'tarefa' in attrs:
            if attrs['tarefa'] != self.instance.tarefa:
                raise serializers.ValidationError({
                    'tarefa': 'Não é permitido trocar a tarefa do comentário.'
                })

        return attrs

    def create(self, validated_data):
        validated_data['autor'] = self.context['request'].user
        return super().create(validated_data)