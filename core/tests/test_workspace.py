from datetime import timedelta

from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import Notificacao, ParticipanteProjeto, Projeto, Tarefa, User
from core.services.notificacoes import prazos


class WorkspaceTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin@workspace.test', 'OriginalPassword123!')
        self.member = User.objects.create_user('member@workspace.test', 'OriginalPassword123!')
        self.other = User.objects.create_user('other@workspace.test', 'OriginalPassword123!')
        self.client.force_authenticate(self.admin)
        result = self.client.post('/api/projetos/', {'nome': 'Kando', 'descricao': 'Real'}, format='json')
        self.project = Projeto.objects.get(pk=result.data['id'])
        ParticipanteProjeto.objects.create(projeto=self.project, usuario=self.member)

    def task(self, **kwargs):
        return Tarefa.objects.create(
            projeto=self.project,
            criador=self.admin,
            responsavel=self.member,
            titulo='API',
            descricao='Real',
            prioridade=2,
            **kwargs,
        )

    def test_notifications_are_private_and_server_generated(self):
        task = self.task()
        self.assertTrue(Notificacao.objects.filter(usuario=self.member, tipo='atribuicao', tarefa=task).exists())
        task.descricao = 'Updated'
        task.save()
        self.assertEqual(Notificacao.objects.filter(usuario=self.member, tipo='alteracao').count(), 1)
        task.save()
        self.assertEqual(Notificacao.objects.filter(usuario=self.member, tipo='alteracao').count(), 1)
        self.client.force_authenticate(self.other)
        result = self.client.get('/api/notificacoes/')
        self.assertEqual(result.data['results'], [])
        notification = Notificacao.objects.filter(usuario=self.member).first()
        self.assertEqual(
            self.client.patch(f'/api/notificacoes/{notification.pk}/', {'lida': True}, format='json').status_code, 404
        )
        self.assertEqual(
            self.client.post('/api/notificacoes/', {'usuario': self.other.pk}, format='json').status_code, 405
        )

    def test_notification_read_delete_and_all_read(self):
        self.task()
        self.client.force_authenticate(self.member)
        notification = Notificacao.objects.filter(usuario=self.member).first()
        url = f'/api/notificacoes/{notification.pk}/'
        self.assertEqual(self.client.patch(url, {'lida': True, 'mensagem': 'Forged'}, format='json').status_code, 200)
        notification.refresh_from_db()
        self.assertTrue(notification.lida)
        self.assertNotEqual(notification.mensagem, 'Forged')
        self.assertEqual(self.client.post('/api/notificacoes/ler-todas/').status_code, 200)
        self.assertFalse(Notificacao.objects.filter(usuario=self.member, lida=False).exists())
        self.assertEqual(self.client.delete(url).status_code, 204)

    def test_deadline_alerts_deduplicate_and_ignore_completed(self):
        near = self.task(prazo=timezone.now() + timedelta(hours=10))
        late = self.task(prazo=timezone.now() - timedelta(days=1))
        self.task(prazo=timezone.now() - timedelta(days=1), situacao='concluida')
        prazos()
        prazos()
        self.assertEqual(Notificacao.objects.filter(tipo='prazo', tarefa=near).count(), 1)
        self.assertEqual(Notificacao.objects.filter(tipo='atraso', tarefa=late).count(), 1)
        self.assertEqual(Notificacao.objects.filter(tipo='atraso').count(), 1)
        notification = Notificacao.objects.get(tipo='atraso', tarefa=late)
        self.client.force_authenticate(self.member)
        self.client.delete(f'/api/notificacoes/{notification.pk}/')
        prazos()
        self.assertFalse(Notificacao.objects.filter(tipo='atraso', tarefa=late, excluida=False).exists())

    def test_membership_role_removal_and_completion_notifications(self):
        membership = ParticipanteProjeto.objects.get(projeto=self.project, usuario=self.member)
        self.client.patch(f'/api/participantes-projeto/{membership.pk}/', {'papel': 'admin'}, format='json')
        self.assertTrue(Notificacao.objects.filter(usuario=self.member, tipo='permissao').exists())
        task = self.task()
        self.client.patch(f'/api/tarefas/{task.pk}/', {'situacao': 'concluida'}, format='json')
        self.assertEqual(Notificacao.objects.filter(tipo='conclusao', tarefa=task).count(), 2)
        self.client.delete(f'/api/participantes-projeto/{membership.pk}/')
        self.assertTrue(Notificacao.objects.filter(usuario=self.member, tipo='remocao').exists())

    def test_profile_fields_and_private_birthday(self):
        response = self.client.patch(
            f'/api/usuarios/{self.admin.pk}/',
            {'name': 'New Name', 'data_nascimento': '2000-01-01', 'token_version': 500},
            format='json',
        )
        self.assertEqual(response.status_code, 200)
        self.admin.refresh_from_db()
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get('/api/usuarios/me/').data['data_nascimento'], '2000-01-01')
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.token_version, 0)
        self.client.force_authenticate(self.other)
        result = self.client.get('/api/usuarios/')
        self.assertTrue(all('data_nascimento' not in u for u in result.data['results']))

    def test_password_validation_and_revokes_access_and_refresh(self):
        self.client.force_authenticate(None)
        tokens = self.client.post(
            '/api/token/', {'email': self.admin.email, 'password': 'OriginalPassword123!'}, format='json'
        ).data
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + tokens['access'])
        endpoint = '/api/usuarios/alterar-senha/'
        data = {
            'senha_atual': 'wrong',
            'nova_senha': 'DifferentPassword456!',
            'confirmar_senha': 'DifferentPassword456!',
        }
        self.assertEqual(self.client.post(endpoint, data, format='json').status_code, 400)
        data['senha_atual'] = 'OriginalPassword123!'
        data['confirmar_senha'] = 'mismatch'
        self.assertEqual(self.client.post(endpoint, data, format='json').status_code, 400)
        data['confirmar_senha'] = data['nova_senha'] = '123'
        self.assertEqual(self.client.post(endpoint, data, format='json').status_code, 400)
        data['confirmar_senha'] = data['nova_senha'] = 'DifferentPassword456!'
        response = self.client.post(endpoint, data, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.client.get('/api/usuarios/me/').status_code, 401)
        self.client.credentials()
        self.assertEqual(
            self.client.post('/api/token/refresh/', {'refresh': tokens['refresh']}, format='json').status_code, 401
        )
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + response.data['access'])
        self.assertEqual(self.client.get('/api/usuarios/me/').status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('DifferentPassword456!'))
        self.assertNotEqual(self.admin.password, 'DifferentPassword456!')

    def test_account_deletion_cannot_remove_last_administrator(self):
        response = self.client.delete(f'/api/usuarios/{self.admin.pk}/')
        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            ParticipanteProjeto.objects.filter(usuario=self.admin, projeto=self.project, papel='admin').exists()
        )

    def test_participant_cannot_comment_on_someone_elses_task(self):
        task = self.task()
        task.responsavel = self.admin
        task.save()
        self.client.force_authenticate(self.member)
        response = self.client.post('/api/comentarios/', {'tarefa': task.pk, 'conteudo': 'Forbidden'}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_project_deletion_with_notifications_and_tasks_has_no_orphans(self):
        self.task()
        self.assertTrue(Notificacao.objects.filter(projeto=self.project).exists())
        response = self.client.delete(f'/api/projetos/{self.project.pk}/')
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Projeto.objects.filter(pk=self.project.pk).exists())
        self.assertFalse(Tarefa.objects.filter(projeto_id=self.project.pk).exists())
        self.assertTrue(all(n.projeto_id is None and n.tarefa_id is None for n in Notificacao.objects.all()))
