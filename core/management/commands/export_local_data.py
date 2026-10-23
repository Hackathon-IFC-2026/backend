import os
import sqlite3
import stat
from pathlib import Path

from django.apps import apps
from django.conf import settings
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection

EXCLUDED_MODELS = {'core.passwordresetchallenge'}


def _export_models():
    return [
        *apps.get_app_config('core').get_models(),
        apps.get_model('auth', 'Group'),
    ]


def _record_counts():
    return {
        model._meta.label: model.objects.using('default').count()
        for model in _export_models()
        if model._meta.label_lower not in EXCLUDED_MODELS
    }


def _create_sqlite_backup(source, backup_path):
    with sqlite3.connect(source) as source_db:
        with sqlite3.connect(backup_path) as backup_db:
            source_db.backup(backup_db)


def _create_fixture(fixture_path):
    call_command(
        'dumpdata',
        'core',
        'auth.Group',
        database='default',
        exclude=['core.passwordresetchallenge'],
        natural_foreign=True,
        indent=2,
        output=str(fixture_path),
    )


class Command(BaseCommand):
    help = 'Cria backup do SQLite local e fixture de dados para transferência segura.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--directory',
            required=True,
            help='Diretório privado onde serão criados o backup SQLite e o fixture.',
        )

    def handle(self, *args, **options):
        if connection.vendor != 'sqlite':
            raise CommandError('A exportação só pode ser executada com o banco SQLite local.')

        source_name = settings.DATABASES['default']['NAME']
        if not isinstance(source_name, (str, os.PathLike)) or source_name == ':memory:':
            raise CommandError('O banco SQLite precisa ser um arquivo para criar um backup.')

        source = Path(source_name).resolve()
        if not source.is_file():
            raise CommandError('O arquivo do banco SQLite local não foi encontrado.')

        directory = Path(options['directory']).expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if stat.S_IMODE(directory.stat().st_mode) & 0o077:
            raise CommandError('O diretório de saída precisa ser privado; aplique chmod 700.')

        backup_path = directory / 'kando-local.sqlite3'
        fixture_path = directory / 'kando-local.json'
        if backup_path.exists() or fixture_path.exists():
            raise CommandError('Os arquivos de saída já existem; escolha um diretório vazio.')

        created_outputs = []
        try:
            for output_path in (backup_path, fixture_path):
                descriptor = os.open(output_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(descriptor)
                created_outputs.append(output_path)
            _create_sqlite_backup(source, backup_path)
            _create_fixture(fixture_path)
        except Exception:
            for output_path in created_outputs:
                output_path.unlink(missing_ok=True)
            raise

        self.stdout.write(self.style.SUCCESS('Backup SQLite e fixture de transferência criados.'))
        self.stdout.write(f'Backup: {backup_path}')
        self.stdout.write(f'Fixture: {fixture_path}')
        self.stdout.write('Registros exportados:')
        for label, count in _record_counts().items():
            self.stdout.write(f'  {label}: {count}')
        self.stdout.write('Desafios de recuperação de senha não são exportados.')
