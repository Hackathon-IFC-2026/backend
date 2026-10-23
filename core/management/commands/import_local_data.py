import json
from pathlib import Path

from django.apps import apps
from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection, transaction
from django.db.migrations.executor import MigrationExecutor

EXCLUDED_MODELS = {'core.passwordresetchallenge'}
FIXTURE_MODELS = {
    *(model._meta.label_lower for model in apps.get_app_config('core').get_models()),
    'auth.group',
} - EXCLUDED_MODELS


def _data_models():
    return [
        model
        for model in (
            *apps.get_app_config('core').get_models(),
            apps.get_model('auth', 'Group'),
        )
        if model._meta.label_lower not in EXCLUDED_MODELS
    ]


def _record_counts():
    return {model._meta.label: model.objects.using('default').count() for model in _data_models()}


def _table_names():
    tables = set()
    for model in _data_models():
        tables.add(model._meta.db_table)
        tables.update(field.remote_field.through._meta.db_table for field in model._meta.local_many_to_many)
    return sorted(tables)


def _validate_fixture(fixture_path):
    try:
        with fixture_path.open(encoding='utf-8') as fixture_file:
            fixture = json.load(fixture_file)
    except (OSError, json.JSONDecodeError) as exc:
        raise CommandError('Não foi possível ler o fixture JSON indicado.') from exc

    if not isinstance(fixture, list):
        raise CommandError('O fixture precisa conter uma lista de objetos serializados pelo Django.')

    model_counts = {}
    for entry in fixture:
        model_label = entry.get('model') if isinstance(entry, dict) else None
        if not isinstance(model_label, str) or model_label not in FIXTURE_MODELS:
            raise CommandError('O fixture contém um modelo fora do escopo permitido.')
        model_counts[model_label] = model_counts.get(model_label, 0) + 1
    return model_counts


def _import_fixture(fixture_path, fixture_counts):
    with transaction.atomic(using='default'):
        quote_name = connection.ops.quote_name
        table_list = ', '.join(quote_name(table) for table in _table_names())
        with connection.cursor() as cursor:
            cursor.execute(f'LOCK TABLE {table_list} IN SHARE ROW EXCLUSIVE MODE')

        existing_counts = _record_counts()
        populated = {label: count for label, count in existing_counts.items() if count}
        if populated:
            summary = ', '.join(f'{label}={count}' for label, count in populated.items())
            raise CommandError(
                'Destino contém registros; nenhuma importação foi feita. '
                f'Crie um plano de merge manual. Contagens: {summary}'
            )

        call_command('loaddata', str(fixture_path), database='default', verbosity=0)
        imported_counts = _record_counts()
        for label, expected_count in fixture_counts.items():
            model = apps.get_model(label)
            actual_count = imported_counts[model._meta.label]
            if actual_count != expected_count:
                raise CommandError(f'Contagem divergente para {model._meta.label}; a transação será revertida.')
    return imported_counts


class Command(BaseCommand):
    help = 'Importa fixture local apenas em PostgreSQL com tabelas de dados vazias.'

    def add_arguments(self, parser):
        parser.add_argument(
            'fixture',
            nargs='?',
            help='Arquivo JSON criado por export_local_data.',
        )
        parser.add_argument(
            '--check-only',
            action='store_true',
            help='Mostra banco, migrations e contagens sem importar registros.',
        )
        parser.add_argument(
            '--confirm-empty-destination',
            action='store_true',
            help='Confirma a importação somente se todas as tabelas de dados estiverem vazias.',
        )

    def handle(self, *args, **options):
        if connection.vendor != 'postgresql':
            raise CommandError('A importação exige PostgreSQL; nenhum dado foi alterado.')
        if options['check_only']:
            if options['confirm_empty_destination']:
                raise CommandError('Não combine --check-only com --confirm-empty-destination.')
            self._check_migrations()
            self.stdout.write('Banco de destino: PostgreSQL.')
            self._write_counts(_record_counts())
            return

        if not options['fixture']:
            raise CommandError('Informe o caminho do fixture criado por export_local_data.')
        if not options['confirm_empty_destination']:
            raise CommandError('A importação exige --confirm-empty-destination.')

        fixture_path = Path(options['fixture']).expanduser().resolve()
        fixture_counts = _validate_fixture(fixture_path)
        self._check_migrations()

        try:
            imported_counts = _import_fixture(fixture_path, fixture_counts)
        except CommandError:
            raise
        except Exception as exc:
            raise CommandError(f'Falha na importação; a transação foi revertida ({type(exc).__name__}).') from exc

        self.stdout.write(self.style.SUCCESS('Fixture importado; IDs e relações foram preservados.'))
        self._write_counts(imported_counts)
        self.stdout.write('Django loaddata atualizou as sequências do PostgreSQL.')

    def _check_migrations(self):
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            pending = ', '.join(migration.name for migration, _ in plan)
            raise CommandError(
                f'Existem migrations pendentes: {pending}. Aplique-as separadamente antes da importação.'
            )

    def _write_counts(self, counts):
        self.stdout.write('Contagens por modelo (sem desafios de recuperação):')
        for label, count in counts.items():
            self.stdout.write(f'  {label}: {count}')
