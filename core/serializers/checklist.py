from rest_framework import serializers

from core.models import Checklist


class ChecklistSerializer(serializers.ModelSerializer):
    class Meta:
        model = Checklist
        fields = '__all__'

    def validate_tarefa(self, tarefa):
        usuario = self.context['request'].user

        participa = tarefa.projeto.participantes.filter(
            usuario=usuario
        ).exists()

        if not participa:
            raise serializers.ValidationError(
                'Você precisa participar do projeto para acessar este checklist.'
            )

        if tarefa.bloqueada:
            raise serializers.ValidationError(
                'Não é possível alterar o checklist de uma tarefa bloqueada.'
            )

        return tarefa

    def validate(self, attrs):
        if self.instance is not None:
            tarefa = self.instance.tarefa

            if tarefa.bloqueada:
                raise serializers.ValidationError(
                    'Não é possível alterar o checklist de uma tarefa bloqueada.'
                )

            if 'tarefa' in attrs and attrs['tarefa'] != tarefa:
                raise serializers.ValidationError({
                    'tarefa': 'Não é permitido transferir o item para outra tarefa.'
                })

        return attrs