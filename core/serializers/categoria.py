from rest_framework.serializers import ModelSerializer, SlugRelatedField

from core.models import Categoria

from rest_framework import serializers


class CategoriaSerializer(ModelSerializer):


    class Meta:
        model = Categoria
        fields = '__all__'