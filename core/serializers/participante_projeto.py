from rest_framework import serializers

from core.models import ParticipanteProjeto, User


class ParticipanteProjetoSerializer(serializers.ModelSerializer):
    usuario = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all()
    )

    class Meta:
        model = ParticipanteProjeto
        fields = '__all__'
        read_only_fields = (
            'id',
            'entrou_em',
        )

    def validate(self, attrs):
        request = self.context['request']
        usuario_logado = request.user

        if self.instance is None:
            projeto = attrs['projeto']

            ja_participa = projeto.participantes.filter(
                usuario=attrs['usuario']
            ).exists()

            if ja_participa:
                raise serializers.ValidationError({
                    'usuario': 'Este usuário já participa do projeto.'
                })

        else:
            projeto = self.instance.projeto

            if 'projeto' in attrs and attrs['projeto'] != projeto:
                raise serializers.ValidationError({
                    'projeto': 'Não é permitido transferir um participante para outro projeto.'
                })

            papel_atual = self.instance.papel
            novo_papel = attrs.get('papel', papel_atual)

            if (
                papel_atual == ParticipanteProjeto.Papel.ADMIN
                and novo_papel != ParticipanteProjeto.Papel.ADMIN
            ):
                quantidade_admins = projeto.participantes.filter(
                    papel=ParticipanteProjeto.Papel.ADMIN
                ).count()

                if quantidade_admins <= 1:
                    raise serializers.ValidationError({
                        'papel': 'O projeto precisa ter pelo menos um administrador.'
                    })

        return attrs