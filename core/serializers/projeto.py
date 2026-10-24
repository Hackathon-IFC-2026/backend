from django.db import transaction
from rest_framework import serializers

from core.models import ParticipanteProjeto, Projeto


class ProjetoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Projeto
        fields = '__all__'
        read_only_fields = ('id', 'criado_em', 'atualizado_em', 'criado_por')

    @transaction.atomic
    def create(self, validated_data):
        projeto = Projeto.objects.create(criado_por=self.context['request'].user, **validated_data)
        ParticipanteProjeto.objects.create(projeto=projeto, usuario=projeto.criado_por, papel='admin')
        return projeto
