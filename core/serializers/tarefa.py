from rest_framework import serializers

from core.models import Tarefa, User
from django.utils import timezone

class TarefaSerializer(serializers.ModelSerializer):
    bloqueada = serializers.BooleanField(read_only=True)
    atrasada = serializers.BooleanField(read_only=True)
    responsavel = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Tarefa
        fields = '__all__'
        read_only_fields = (
            'id',
            'criador',
            'concluida_em',
            'criada_em',
            'atualizada_em',
        )

    def validate_projeto(self, projeto):
        usuario = self.context['request'].user

        participa = projeto.participantes.filter(usuario=usuario).exists()

        if not participa:
            raise serializers.ValidationError('Você precisa participar do projeto para criar tarefas.')

        return projeto

    def get_fields(self):
        fields = super().get_fields()

        if self.instance is not None:
            fields['projeto'].read_only = True

        return fields

    def validate(self, attrs):
        usuario = self.context['request'].user

        # Na criação, a validação do projeto já é feita em validate_projeto().
        if self.instance is None:
            return attrs

        projeto = self.instance.projeto

        eh_admin = projeto.participantes.filter(
            usuario=usuario,
            papel='admin'
        ).exists()

        responsavel_enviado = (
            'responsavel' in attrs
            and attrs['responsavel'] != self.instance.responsavel
        )

        if responsavel_enviado and not eh_admin:
            raise serializers.ValidationError({
                'responsavel': 'Somente administradores podem alterar o responsável.'
            })

        if responsavel_enviado:
            responsavel = attrs['responsavel']

            if responsavel is not None:
                participa = projeto.participantes.filter(
                    usuario=responsavel
                ).exists()

                if not participa:
                    raise serializers.ValidationError({
                        'responsavel': 'O responsável precisa participar deste projeto.'
                    })

        return attrs

    def create(self, validated_data):
        usuario = self.context['request'].user

        validated_data['criador'] = usuario
        validated_data['responsavel'] = usuario

        situacao = validated_data.get(
            'situacao',
            Tarefa.Situacao.EM_ABERTO
        )

        if situacao == Tarefa.Situacao.CONCLUIDA:
            validated_data['concluida_em'] = timezone.now()
        else:
            validated_data['concluida_em'] = None

        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        usuario = self.context['request'].user
        projeto = instance.projeto

        eh_admin = projeto.participantes.filter(
            usuario=usuario,
            papel='admin'
        ).exists()

        responsavel_enviado = 'responsavel' in validated_data

        if instance.bloqueada:
            if not eh_admin or not responsavel_enviado:
                raise serializers.ValidationError(
                    'Esta tarefa está bloqueada. Somente um administrador '
                    'pode atribuir um novo responsável.'
                )
            if set(validated_data.keys()) != {'responsavel'}:
                raise serializers.ValidationError(
                    'Enquanto a tarefa estiver bloqueada, só é permitido atribuir um responsável.'
                )

            if validated_data['responsavel'] is None:
                raise serializers.ValidationError({
                    'responsavel': 'Escolha um responsável para desbloquear a tarefa.'
                })

        situacao = validated_data.get(
            'situacao',
            instance.situacao
        )

        if situacao == Tarefa.Situacao.CONCLUIDA:
            if instance.situacao != Tarefa.Situacao.CONCLUIDA:
                validated_data['concluida_em'] = timezone.now()
        else:
            validated_data['concluida_em'] = None

        return super().update(instance, validated_data)
