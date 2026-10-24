import secrets
from getpass import getpass

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.db import IntegrityError, transaction

from core.models import User


class Command(BaseCommand):
    help = 'Prepara uma conta local não privilegiada para testar a recuperação de senha.'

    def handle(self, *args, **options):
        if not (settings.DEBUG and settings.LOCAL_DEVELOPMENT):
            raise CommandError(
                'Este comando só pode ser executado com DEBUG e LOCAL_DEVELOPMENT ativos.'
            )

        email = getpass('E-mail de teste controlado por você (entrada oculta): ').strip()
        try:
            validate_email(email)
        except ValidationError as exc:
            raise CommandError('O endereço informado não tem um formato válido.') from exc

        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user is not None:
            if not existing_user.is_active:
                raise CommandError(
                    'A conta correspondente está inativa; nenhuma alteração foi feita.'
                )
            self.stdout.write('A conta já existe e está ativa; nenhuma alteração foi feita.')
            return

        confirmation = getpass('Confirme o endereço (entrada oculta): ').strip()
        if confirmation.casefold() != email.casefold():
            raise CommandError('A confirmação não corresponde; nenhuma conta foi criada.')

        initial_password = secrets.token_urlsafe(48)
        try:
            with transaction.atomic():
                if User.objects.filter(email__iexact=email).exists():
                    raise CommandError(
                        'A conta foi criada em paralelo; nenhuma alteração foi feita.'
                    )
                User.objects.create_user(
                    email=email,
                    password=initial_password,
                    name='Conta local de teste',
                )
        except IntegrityError as exc:
            raise CommandError(
                'Não foi possível criar a conta; verifique se ela já existe.'
            ) from exc

        self.stdout.write(
            self.style.SUCCESS(
                'Conta local de teste criada e ativa no banco configurado. '
                'A senha inicial aleatória não foi exibida nem armazenada em texto puro.'
            )
        )
