from rest_framework import serializers

from core.models import MaterialApoio


class MaterialApoioSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaterialApoio
        fields = '__all__'
