from rest_framework import serializers

from core.models import ParticipanteProjeto


class ParticipanteProjetoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParticipanteProjeto
        fields = '__all__'
