from datetime import timedelta
from io import BytesIO
from tempfile import TemporaryDirectory

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APITestCase

from core.models import ParticipanteProjeto, Projeto, Tarefa, User


class ProfilePlanningTests(APITestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.settings = override_settings(MEDIA_ROOT=self.media.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        self.addCleanup(self.media.cleanup)
        self.user = User.objects.create_user('planning@test.example', 'OriginalPassword123!')
        self.other = User.objects.create_user('other-planning@test.example', 'OriginalPassword123!')
        self.client.force_authenticate(self.user)

    def image(self, format='PNG'):
        stream = BytesIO()
        Image.new('RGB', (180, 120), color='green').save(stream, format=format)
        return SimpleUploadedFile('avatar.' + format.lower(), stream.getvalue(), content_type='image/' + format.lower())

    def test_registration_requires_valid_birthday_but_old_accounts_can_login(self):
        self.client.force_authenticate(None)
        data = {'name': 'New', 'email': 'new-birthday@test.example', 'password': 'OriginalPassword123!'}
        self.assertEqual(self.client.post('/api/registro/', data, format='json').status_code, 400)
        data['data_nascimento'] = (timezone.localdate() + timedelta(days=1)).isoformat()
        self.assertEqual(self.client.post('/api/registro/', data, format='json').status_code, 400)
        data['data_nascimento'] = '2000-02-30'
        self.assertEqual(self.client.post('/api/registro/', data, format='json').status_code, 400)
        data['data_nascimento'] = '2000-02-29'
        result = self.client.post('/api/registro/', data, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(User.objects.get(email=data['email']).data_nascimento.isoformat(), '2000-02-29')
        result = self.client.post(
            '/api/token/', {'email': self.user.email, 'password': 'OriginalPassword123!'}, format='json'
        )
        self.assertEqual(result.status_code, 200)

    def test_photo_upload_me_url_replacement_and_removal(self):
        url = f'/api/usuarios/{self.user.pk}/'
        result = self.client.patch(url, {'foto': self.image()}, format='multipart')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertTrue(result.data['foto'].startswith('http://testserver/media/'))
        self.user.refresh_from_db()
        first_name = self.user.foto.name
        self.assertTrue(self.user.foto.storage.exists(first_name))
        with Image.open(self.user.foto) as saved:
            self.assertEqual(saved.format, 'JPEG')
        self.user.foto.close()
        self.client.force_authenticate(self.user)
        result = self.client.get('/api/usuarios/me/')
        self.assertTrue(result.data['foto'].startswith('http://testserver/media/'))
        with self.captureOnCommitCallbacks(execute=True):
            result = self.client.patch(url, {'foto': self.image('WEBP')}, format='multipart')
        self.assertEqual(result.status_code, 200)
        self.assertFalse(self.user.foto.storage.exists(first_name))
        self.user.refresh_from_db()
        second_name = self.user.foto.name
        with self.captureOnCommitCallbacks(execute=True):
            result = self.client.patch(url, {'foto': None}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertIsNone(result.data['foto'])
        self.assertFalse(self.user.foto.storage.exists(second_name))

    def test_invalid_oversized_and_unsupported_images_are_rejected(self):
        url = f'/api/usuarios/{self.user.pk}/'
        fake = SimpleUploadedFile('fake.jpg', b'not-an-image', content_type='image/jpeg')
        self.assertEqual(self.client.patch(url, {'foto': fake}, format='multipart').status_code, 400)
        self.assertEqual(self.client.patch(url, {'foto': self.image('GIF')}, format='multipart').status_code, 400)
        large = self.image()
        content = large.read() + b'0' * (5 * 1024 * 1024)
        large = SimpleUploadedFile('large.png', content, content_type='image/png')
        self.assertEqual(self.client.patch(url, {'foto': large}, format='multipart').status_code, 400)

    def test_photo_and_birthday_are_editable_only_by_owner(self):
        self.client.force_authenticate(self.other)
        response = self.client.patch(f'/api/usuarios/{self.user.pk}/', {'foto': self.image()}, format='multipart')
        self.assertEqual(response.status_code, 404)
        response = self.client.patch(f'/api/usuarios/{self.user.pk}/', {'data_nascimento': '2000-01-01'}, format='json')
        self.assertEqual(response.status_code, 404)
        result = self.client.get('/api/usuarios/')
        self.assertTrue(all('data_nascimento' not in u for u in result.data['results']))

    def test_start_date_persists_and_partial_edits_validate_both_dates(self):
        result = self.client.post('/api/projetos/', {'nome': 'Planning', 'descricao': 'Real'}, format='json')
        project = Projeto.objects.get(pk=result.data['id'])
        ParticipanteProjeto.objects.create(projeto=project, usuario=self.other)
        data = {
            'projeto': project.pk,
            'titulo': 'Dates',
            'descricao': 'Real',
            'prioridade': 2,
            'responsavel': self.other.pk,
            'data_inicio': '2026-10-10',
            'prazo': '2026-10-15T23:59:59-03:00',
        }
        result = self.client.post('/api/tarefas/', data, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data['data_inicio'], '2026-10-10')
        url = f'/api/tarefas/{result.data["id"]}/'
        self.assertEqual(self.client.patch(url, {'data_inicio': '2026-10-16'}, format='json').status_code, 400)
        self.assertEqual(self.client.patch(url, {'prazo': '2026-10-09T23:59:59-03:00'}, format='json').status_code, 400)
        self.client.force_authenticate(self.other)
        result = self.client.patch(url, {'data_inicio': '2026-10-12'}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(Tarefa.objects.get(pk=result.data['id']).data_inicio.isoformat(), '2026-10-12')
        self.assertEqual(self.client.patch(url, {'data_inicio': None, 'prazo': None}, format='json').status_code, 200)
