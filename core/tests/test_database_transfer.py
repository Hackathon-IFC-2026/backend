from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase

from core.management.commands.import_local_data import _validate_fixture


class DatabaseTransferCommandTests(SimpleTestCase):
    def setUp(self):
        self.temporary_directory = TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)

    def test_import_command_refuses_non_postgresql_database(self):
        with self.assertRaisesMessage(CommandError, 'A importação exige PostgreSQL'):
            call_command(
                'import_local_data',
                'unused-fixture.json',
                '--confirm-empty-destination',
                stdout=StringIO(),
            )

    def test_import_fixture_rejects_models_outside_transfer_scope(self):
        fixture_path = self.create_temp_file(
            'fixture.json',
            '[{"model":"auth.user","pk":1,"fields":{}}]',
        )

        with self.assertRaisesMessage(CommandError, 'fora do escopo permitido'):
            _validate_fixture(fixture_path)

    def test_import_fixture_counts_only_allowed_models(self):
        fixture_path = self.create_temp_file(
            'fixture.json',
            '[{"model":"core.user","pk":1,"fields":{}},{"model":"core.board","pk":1,"fields":{}}]',
        )

        assert _validate_fixture(fixture_path) == {'core.user': 1, 'core.board': 1}

    def create_temp_file(self, name, content):
        path = Path(self.temporary_directory.name) / name
        path.write_text(content, encoding='utf-8')
        return path
