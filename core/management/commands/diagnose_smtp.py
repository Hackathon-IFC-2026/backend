import smtplib
from datetime import timedelta
from email.utils import parseaddr
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.template.exceptions import TemplateDoesNotExist, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils import timezone
from dotenv import dotenv_values

SMTP_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
MAX_SMTP_PORT = 65535
SMTP_SETTINGS = (
    'EMAIL_BACKEND',
    'EMAIL_HOST',
    'EMAIL_PORT',
    'EMAIL_HOST_USER',
    'EMAIL_HOST_PASSWORD',
    'EMAIL_USE_TLS',
    'EMAIL_USE_SSL',
    'DEFAULT_FROM_EMAIL',
)


def _dotenv_mismatches(dotenv, effective_settings):
    mismatches = []
    for name in SMTP_SETTINGS:
        if name not in dotenv or dotenv[name] is None:
            continue
        dotenv_value = dotenv[name]
        effective_value = effective_settings[name]
        if name in {'EMAIL_USE_TLS', 'EMAIL_USE_SSL'}:
            dotenv_value = dotenv_value.strip().lower()
            effective_value = effective_value.strip().lower()
        elif name == 'EMAIL_PORT':
            dotenv_value = dotenv_value.strip()
            effective_value = effective_value.strip()
        if effective_value != dotenv_value:
            mismatches.append(name)
    return mismatches


def _configuration_source(name, dotenv):
    if name in settings.ENV_KEYS_BEFORE_DOTENV:
        return 'ambiente do processo'
    if name in dotenv and dotenv[name] is not None:
        return '.env'
    return 'padrão/fallback'


def _render_test_bodies():
    invitation_id = '00000000-0000-0000-0000-000000000000'
    context = {
        'inviter_name': 'Alex Demonstração — convite de teste',
        'task_title': 'Tarefa de demonstração — revisar o planejamento',
        'board_title': 'Quadro de demonstração',
        'accept_url': (f'https://kando.example/convites/{invitation_id}/aceitar'),
        'decline_url': (f'https://kando.example/convites/{invitation_id}/recusar'),
        'expires_at': timezone.now() + timedelta(days=7),
    }
    try:
        return (
            render_to_string('core/emails/task_invitation.txt', context),
            render_to_string('core/emails/task_invitation.html', context),
        )
    except (TemplateDoesNotExist, TemplateSyntaxError, ValueError) as exc:
        raise CommandError(f'Não foi possível preparar o modelo do e-mail de teste ({type(exc).__name__}).') from exc


class Command(BaseCommand):
    help = (
        'Verifica a configuração SMTP sem exibir credenciais e, opcionalmente, '
        'envia uma mensagem para um endereço autorizado.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--recipient',
            help='Endereço de teste que você controla ou tem autorização para usar.',
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Valida a configuração sem enviar uma mensagem.',
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        check_only = options['check_only']
        if not check_only and not recipient:
            raise CommandError('Informe --recipient ou use --check-only.')
        if check_only and recipient:
            raise CommandError('Use --check-only sem --recipient.')

        failures = self._report_configuration()
        if failures:
            raise CommandError('Configuração SMTP incompleta ou inconsistente; corrija os itens indicados.')
        if check_only:
            self.stdout.write(self.style.SUCCESS('Verificação de configuração concluída; nenhuma mensagem enviada.'))
            return

        try:
            validate_email(recipient)
        except ValidationError as exc:
            raise CommandError('O endereço de teste não tem um formato válido.') from exc

        text_body, html_body = _render_test_bodies()
        try:
            connection = get_connection(fail_silently=False)
        except (OSError, smtplib.SMTPException, ImproperlyConfigured, ValueError) as exc:
            raise CommandError(f'Não foi possível preparar o backend SMTP ({type(exc).__name__}).') from exc

        try:
            connection.open()
        except (OSError, smtplib.SMTPException, ImproperlyConfigured, ValueError) as exc:
            try:
                connection.close()
            except (OSError, smtplib.SMTPException) as close_exc:
                self.stderr.write(f'Aviso: erro ao encerrar a conexão SMTP ({type(close_exc).__name__}).')
            raise CommandError(
                f'Falha ao conectar ou autenticar no SMTP ({type(exc).__name__}); '
                'nenhuma mensagem foi confirmada como aceita.'
            ) from exc

        message = EmailMultiAlternatives(
            subject='Kando — convite de demonstração para uma tarefa',
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
            connection=connection,
        )
        message.attach_alternative(html_body, 'text/html')
        try:
            accepted_count = message.send(fail_silently=False)
        except (OSError, smtplib.SMTPException, ImproperlyConfigured, ValueError) as exc:
            raise CommandError(
                f'Falha ao submeter a mensagem ao SMTP ({type(exc).__name__}); consulte os registros do provedor.'
            ) from exc
        finally:
            try:
                connection.close()
            except (OSError, smtplib.SMTPException) as exc:
                self.stderr.write(f'Aviso: erro ao encerrar a conexão SMTP ({type(exc).__name__}).')

        if accepted_count != 1:
            raise CommandError('O backend não confirmou a aceitação da mensagem para o destinatário.')

        self.stdout.write(
            self.style.SUCCESS(
                'O servidor SMTP aceitou a mensagem para processamento. Isso não confirma entrega na caixa de entrada.'
            )
        )

    def _report_configuration(self):
        sender = parseaddr(settings.DEFAULT_FROM_EMAIL)[1].strip().casefold()
        authenticated_user = settings.EMAIL_HOST_USER.strip().casefold()
        dotenv_file = Path(settings.ENV_FILE)
        dotenv = dotenv_values(dotenv_file) if dotenv_file.is_file() else {}
        effective_settings = {
            'EMAIL_BACKEND': settings.EMAIL_BACKEND,
            'EMAIL_HOST': settings.EMAIL_HOST,
            'EMAIL_PORT': str(settings.EMAIL_PORT),
            'EMAIL_HOST_USER': settings.EMAIL_HOST_USER,
            'EMAIL_HOST_PASSWORD': settings.EMAIL_HOST_PASSWORD,
            'EMAIL_USE_TLS': str(settings.EMAIL_USE_TLS).lower(),
            'EMAIL_USE_SSL': str(settings.EMAIL_USE_SSL).lower(),
            'DEFAULT_FROM_EMAIL': settings.DEFAULT_FROM_EMAIL,
        }
        defined_dotenv_settings = [name for name in SMTP_SETTINGS if name in dotenv and dotenv[name] is not None]
        mismatches = _dotenv_mismatches(dotenv, effective_settings)

        sender_matches = bool(sender and sender == authenticated_user)
        checks = (
            (
                'backend SMTP',
                settings.EMAIL_BACKEND == SMTP_BACKEND,
            ),
            ('host configurado', bool(settings.EMAIL_HOST.strip())),
            ('porta válida', 1 <= settings.EMAIL_PORT <= MAX_SMTP_PORT),
            (
                'usuário e senha SMTP configurados',
                bool(settings.EMAIL_HOST_USER.strip() and settings.EMAIL_HOST_PASSWORD),
            ),
            ('exatamente um de TLS/SSL habilitado', bool(settings.EMAIL_USE_TLS) != bool(settings.EMAIL_USE_SSL)),
            ('remetente igual ao usuário SMTP', sender_matches),
        )

        self.stdout.write('Configuração de e-mail efetivamente carregada:')
        self.stdout.write(f'  Arquivo .env da raiz presente: {"sim" if dotenv_file.is_file() else "não"}')
        self.stdout.write(f'  Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'  Host: {settings.EMAIL_HOST or "(vazio)"}')
        self.stdout.write(f'  Porta: {settings.EMAIL_PORT}')
        self.stdout.write(f'  STARTTLS: {"ativado" if settings.EMAIL_USE_TLS else "desativado"}')
        self.stdout.write(f'  SSL implícito: {"ativado" if settings.EMAIL_USE_SSL else "desativado"}')
        self.stdout.write(
            f'  Credenciais configuradas: '
            f'{"sim" if settings.EMAIL_HOST_USER.strip() and settings.EMAIL_HOST_PASSWORD else "não"}'
        )
        self.stdout.write(f'  Remetente corresponde ao usuário SMTP: {"sim" if sender_matches else "não"}')
        self.stdout.write('  Origem efetiva das configurações (valores omitidos):')
        for name in SMTP_SETTINGS:
            self.stdout.write(f'    {name}: {_configuration_source(name, dotenv)}')
        if mismatches:
            self.stdout.write(
                '  Atenção: variáveis do processo diferem de valores no .env; '
                'o processo tem precedência. Nenhum valor foi exibido.'
            )
        elif defined_dotenv_settings:
            self.stdout.write(
                f'  {len(defined_dotenv_settings)} valores definidos no .env correspondem '
                'à configuração efetiva (sem exibir valores).'
            )
        elif dotenv_file.is_file():
            self.stdout.write('  O .env não define configurações SMTP; confira as origens acima.')

        failures = []
        for label, passed in checks:
            self.stdout.write(f'  {"OK" if passed else "FALHA"}: {label}')
            if not passed:
                failures.append(label)
        return failures
