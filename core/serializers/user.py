from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from core.models import User


class BirthdayValidationMixin:
    def validate_data_nascimento(self, value):
        from django.utils import timezone

        if value and value > timezone.localdate():
            raise serializers.ValidationError('A data de nascimento não pode estar no futuro.')
        return value


class UserSerializer(BirthdayValidationMixin, ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'name',
            'data_nascimento',
            'foto',
            'is_active',
            'is_staff',
            'is_superuser',
            'last_login',
            'groups',
        ]
        read_only_fields = ('id', 'is_active', 'is_staff', 'is_superuser', 'last_login', 'groups')
        depth = 1

    def validate_foto(self, arquivo):
        if arquivo is None:
            return arquivo
        from io import BytesIO
        from uuid import uuid4

        from django.core.files.base import ContentFile
        from PIL import Image, UnidentifiedImageError

        if arquivo.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('A imagem deve ter no máximo 5 MB.')
        try:
            with Image.open(arquivo) as imagem:
                if imagem.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise serializers.ValidationError('Envie uma imagem JPG, PNG ou WebP.')
                if imagem.width * imagem.height > 20_000_000:
                    raise serializers.ValidationError('A resolução da imagem é muito grande.')
                imagem.verify()
            arquivo.seek(0)
            with Image.open(arquivo) as imagem:
                from PIL import ImageOps

                imagem = ImageOps.exif_transpose(imagem).convert('RGB')
                imagem.thumbnail((1024, 1024))
                saida = BytesIO()
                imagem.save(saida, format='JPEG', quality=90)
            return ContentFile(saida.getvalue(), name=str(uuid4()) + '.jpg')
        except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
            raise serializers.ValidationError('O arquivo enviado não é uma imagem válida.')

    def update(self, instance, validated_data):
        from django.db import transaction

        anterior = instance.foto.name if instance.foto else None
        storage = instance.foto.storage
        alterando = 'foto' in validated_data
        usuario = super().update(instance, validated_data)
        if alterando and anterior and anterior != (usuario.foto.name if usuario.foto else None):
            transaction.on_commit(lambda: storage.delete(anterior), robust=True)
        return usuario


class UserRegistrationSerializer(BirthdayValidationMixin, ModelSerializer):
    data_nascimento = serializers.DateField(required=True, allow_null=False)
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['id', 'email', 'name', 'data_nascimento', 'password']

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class AlterarSenhaSerializer(serializers.Serializer):
    senha_atual = serializers.CharField(write_only=True, trim_whitespace=False)
    nova_senha = serializers.CharField(write_only=True, trim_whitespace=False)
    confirmar_senha = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError

        user = self.context['request'].user
        if not user.check_password(attrs['senha_atual']):
            raise serializers.ValidationError({'senha_atual': 'Senha atual incorreta.'})
        if attrs['nova_senha'] != attrs['confirmar_senha']:
            raise serializers.ValidationError({'confirmar_senha': 'As senhas não coincidem.'})
        try:
            validate_password(attrs['nova_senha'], user=user)
        except ValidationError as exc:
            raise serializers.ValidationError({'nova_senha': exc.messages})
        return attrs


class UserDirectorySerializer(ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'name', 'email', 'foto']
        read_only_fields = fields
