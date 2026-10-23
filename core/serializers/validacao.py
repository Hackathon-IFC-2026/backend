from rest_framework.serializers import ModelSerializer, SlugRelatedField

from core.models import Validacao

from rest_framework import serializers


class ValidacaoSerializer(ModelSerializer):


    class Meta:
        model = Validacao
        fields = '__all__'