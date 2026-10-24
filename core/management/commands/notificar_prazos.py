from django.core.management.base import BaseCommand

from core.services.notificacoes import prazos


class Command(BaseCommand):
    help = 'Registra alertas de prazo sem duplicá-los. Agendar a cada 5 minutos.'

    def handle(self, *args, **options):
        prazos()
        self.stdout.write('Alertas de prazo atualizados.')
