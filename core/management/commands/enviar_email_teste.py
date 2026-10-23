from django.core.management.base import CommandError

from core.management.commands.diagnose_smtp import Command as SMTPDiagnosticCommand


class Command(SMTPDiagnosticCommand):
    help = 'Envia um e-mail HTML de teste usando o SMTP real configurado no Kando.'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            nargs='?',
            help='Endereço de teste que você controla ou tem autorização para usar.',
        )
        parser.add_argument(
            '--recipient',
            dest='recipient_option',
            help='Endereço de teste que você controla ou tem autorização para usar.',
        )

    def handle(self, *args, **options):
        recipient = options.get('recipient_option') or options.get('recipient')
        if not recipient:
            self.stdout.write('Endereço de e-mail autorizado para o teste: ', ending='')
            recipient = self.stdin.readline().strip()
        if not recipient:
            raise CommandError('É necessário informar um endereço de destino.')

        return super().handle(
            *args,
            recipient=recipient,
            check_only=False,
        )
