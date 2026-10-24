from rest_framework import serializers

from core.models import Validacao


class ValidacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Validacao
        fields = '__all__'
