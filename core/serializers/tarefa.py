from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from core.models import Tarefa, User
from core.project_permissions import administra, participa


class TarefaSerializer(serializers.ModelSerializer):
    bloqueada = serializers.BooleanField(read_only=True)
    atrasada = serializers.BooleanField(read_only=True)
    responsavel = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True), required=False, allow_null=True
    )

    class Meta:
        model = Tarefa
        fields = '__all__'
        read_only_fields = ('id', 'criador', 'concluida_em', 'criada_em', 'atualizada_em')

    def validate(self, attrs):
        user = self.context['request'].user
        projeto = self.instance.projeto if self.instance else attrs['projeto']
        if self.instance and 'projeto' in attrs and attrs['projeto'].pk != self.instance.projeto_id:
            raise serializers.ValidationError({'projeto': 'Não é permitido transferir tarefas entre projetos.'})
        admin = administra(projeto, user)
        if self.instance is None and not admin:
            raise PermissionDenied('Somente o administrador pode criar tarefas.')
        if self.instance and not admin and self.instance.responsavel_id != user.pk:
            raise PermissionDenied('Você não é responsável por esta tarefa.')
        if self.instance and 'responsavel' in attrs and attrs['responsavel'] != self.instance.responsavel and not admin:
            raise PermissionDenied('Somente o administrador pode alterar o responsável.')
        responsavel = attrs.get('responsavel')
        if responsavel and not participa(projeto, responsavel):
            raise serializers.ValidationError({'responsavel': 'O responsável precisa participar do projeto.'})
        inicio = attrs.get('data_inicio', self.instance.data_inicio if self.instance else None)
        prazo = attrs.get('prazo', self.instance.prazo if self.instance else None)
        if inicio and prazo:
            from zoneinfo import ZoneInfo

            dia_prazo = (
                timezone.localtime(prazo, ZoneInfo('America/Sao_Paulo')).date()
                if timezone.is_aware(prazo)
                else prazo.date()
            )
            if inicio > dia_prazo:
                raise serializers.ValidationError({
                    'prazo': 'O prazo de conclusão não pode ser anterior à data de início.'
                })
        return attrs

    def create(self, validated_data):
        validated_data['criador'] = self.context['request'].user
        validated_data.setdefault('responsavel', self.context['request'].user)
        validated_data['concluida_em'] = (
            timezone.now() if validated_data.get('situacao') == Tarefa.Situacao.CONCLUIDA else None
        )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        situacao = validated_data.get('situacao', instance.situacao)
        if situacao != instance.situacao:
            validated_data['concluida_em'] = timezone.now() if situacao == Tarefa.Situacao.CONCLUIDA else None
        return super().update(instance, validated_data)
