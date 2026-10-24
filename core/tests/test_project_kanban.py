from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from rest_framework.test import APITestCase

from core.models import Checklist, Comentario, MaterialApoio, ParticipanteProjeto, Projeto, Tarefa, User


class ProjectKanbanTests(APITestCase):
    def setUp(self):
        self.owner = User.objects.create_user('owner@example.test', 'Password123!')
        self.member = User.objects.create_user('member@example.test', 'Password123!')
        self.other = User.objects.create_user('other@example.test', 'Password123!')
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            '/api/projetos/', {'nome': 'Projeto privado', 'descricao': 'Descrição'}, format='json'
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.project = Projeto.objects.get(pk=response.data['id'])
        ParticipanteProjeto.objects.create(projeto=self.project, usuario=self.member)
        self.task = Tarefa.objects.create(
            projeto=self.project,
            criador=self.owner,
            responsavel=self.member,
            titulo='Task',
            descricao='Real',
            prioridade=2,
        )
        self.project_url = f'/api/projetos/{self.project.pk}/'
        self.task_url = f'/api/tarefas/{self.task.pk}/'

    def test_creator_is_automatic_and_membership_is_atomic(self):
        member = ParticipanteProjeto.objects.get(projeto=self.project, usuario=self.owner)
        self.assertEqual(member.papel, 'admin')
        response = self.client.post(
            '/api/projetos/', {'nome': 'Auto', 'descricao': 'Real', 'criado_por': self.other.pk}, format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['criado_por'], self.owner.pk)
        self.assertTrue(
            ParticipanteProjeto.objects.filter(
                projeto_id=response.data['id'], usuario=self.owner, papel='admin'
            ).exists()
        )

    def test_outsider_cannot_list_read_or_modify_private_data(self):
        Checklist.objects.create(tarefa=self.task, descricao='Check')
        Comentario.objects.create(tarefa=self.task, autor=self.owner, conteudo='Private')
        MaterialApoio.objects.create(
            projeto=self.project, criador=self.owner, titulo='Material', url='https://example.com'
        )
        self.client.force_authenticate(self.other)
        for endpoint in [
            'projetos',
            'tarefas',
            'participantes-projeto',
            'checklists',
            'comentarios',
            'materiais-apoio',
        ]:
            response = self.client.get(f'/api/{endpoint}/')
            self.assertEqual(response.data['results'], [], endpoint)
        self.assertEqual(self.client.get(self.project_url).status_code, 404)
        self.assertEqual(self.client.patch(self.project_url, {'nome': 'No'}, format='json').status_code, 404)
        self.assertEqual(self.client.delete(self.task_url).status_code, 404)

    def test_participant_reads_project_but_cannot_administer_it(self):
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(self.project_url).status_code, 200)
        self.assertEqual(self.client.get(self.task_url).status_code, 200)
        self.assertEqual(self.client.patch(self.project_url, {'nome': 'No'}, format='json').status_code, 403)
        self.assertEqual(self.client.delete(self.project_url).status_code, 403)
        self.assertEqual(
            self.client.post(
                '/api/participantes-projeto/', {'projeto': self.project.pk, 'usuario': self.other.pk}, format='json'
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                '/api/tarefas/',
                {'projeto': self.project.pk, 'titulo': 'No', 'descricao': 'No', 'prioridade': 1},
                format='json',
            ).status_code,
            403,
        )

    def test_responsible_can_edit_only_assigned_tasks(self):
        other_task = Tarefa.objects.create(
            projeto=self.project,
            criador=self.owner,
            responsavel=self.owner,
            titulo='Other',
            descricao='Real',
            prioridade=1,
        )
        self.client.force_authenticate(self.member)
        self.assertEqual(
            self.client.patch(
                self.task_url, {'situacao': 'andamento', 'descricao': 'Edited'}, format='json'
            ).status_code,
            200,
        )
        self.assertEqual(
            self.client.patch(f'/api/tarefas/{other_task.pk}/', {'situacao': 'andamento'}, format='json').status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(self.task_url, {'responsavel': self.owner.pk}, format='json').status_code, 403
        )

    def test_owner_assignment_is_preserved_on_create_and_nonmembers_rejected(self):
        data = {
            'projeto': self.project.pk,
            'titulo': 'Created',
            'descricao': 'Real',
            'prioridade': 3,
            'responsavel': self.member.pk,
        }
        response = self.client.post('/api/tarefas/', data, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data['responsavel'], self.member.pk)
        data['responsavel'] = self.other.pk
        self.assertEqual(self.client.post('/api/tarefas/', data, format='json').status_code, 400)

    def test_completion_reopen_and_owner_edits_unassigned_tasks(self):
        response = self.client.patch(self.task_url, {'situacao': 'concluida'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['concluida_em'])
        response = self.client.patch(self.task_url, {'situacao': 'aberta', 'responsavel': None}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data['concluida_em'])
        self.assertTrue(response.data['bloqueada'])
        self.assertEqual(
            self.client.patch(self.task_url, {'descricao': 'Owner can edit'}, format='json').status_code, 200
        )

    def test_task_cannot_move_to_another_project(self):
        other = Projeto.objects.create(nome='Other', descricao='Real', criado_por=self.owner)
        self.assertEqual(self.client.patch(self.task_url, {'projeto': other.pk}, format='json').status_code, 400)

    def test_last_admin_cannot_be_removed_or_demoted(self):
        membership = ParticipanteProjeto.objects.get(projeto=self.project, usuario=self.owner)
        url = f'/api/participantes-projeto/{membership.pk}/'
        self.assertEqual(self.client.delete(url).status_code, 400)
        self.assertEqual(self.client.patch(url, {'papel': 'participante'}, format='json').status_code, 400)
        self.assertEqual(self.project.participantes.filter(papel='admin').count(), 1)

    def test_promoted_admin_has_equal_rights_and_can_demote_creator(self):
        member = ParticipanteProjeto.objects.get(projeto=self.project, usuario=self.member)
        response = self.client.patch(f'/api/participantes-projeto/{member.pk}/', {'papel': 'admin'}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.patch(self.project_url, {'nome': 'Renamed'}, format='json').status_code, 200)
        self.task.responsavel = self.owner
        self.task.save()
        self.assertEqual(self.client.patch(self.task_url, {'titulo': 'Admin edited'}, format='json').status_code, 200)
        owner = ParticipanteProjeto.objects.get(projeto=self.project, usuario=self.owner)
        self.assertEqual(
            self.client.patch(
                f'/api/participantes-projeto/{owner.pk}/', {'papel': 'participante'}, format='json'
            ).status_code,
            200,
        )
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.patch(self.project_url, {'nome': 'Forbidden'}, format='json').status_code, 403)
        self.assertEqual(
            self.client.patch(f'/api/participantes-projeto/{owner.pk}/', {'papel': 'admin'}, format='json').status_code,
            403,
        )
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.delete(f'/api/participantes-projeto/{owner.pk}/').status_code, 204)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get(self.project_url).status_code, 404)

    def test_roles_are_specific_to_each_project(self):
        other = self.client.post('/api/projetos/', {'nome': 'Second', 'descricao': 'Real'}, format='json')
        member = ParticipanteProjeto.objects.get(projeto=self.project, usuario=self.member)
        self.client.patch(f'/api/participantes-projeto/{member.pk}/', {'papel': 'admin'}, format='json')
        self.client.force_authenticate(self.member)
        self.assertEqual(self.client.get(f'/api/projetos/{other.data["id"]}/').status_code, 404)

    def test_checklist_scoped_to_editable_task(self):
        self.client.force_authenticate(self.member)
        response = self.client.post('/api/checklists/', {'tarefa': self.task.pk, 'descricao': 'Check'}, format='json')
        self.assertEqual(response.status_code, 201)
        item_id = response.data['id']
        other_task = Tarefa.objects.create(
            projeto=self.project,
            criador=self.owner,
            responsavel=self.owner,
            titulo='Other',
            descricao='Real',
            prioridade=1,
        )
        self.assertEqual(
            self.client.post(
                '/api/checklists/', {'tarefa': other_task.pk, 'descricao': 'No'}, format='json'
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(f'/api/checklists/{item_id}/', {'tarefa': other_task.pk}, format='json').status_code, 400
        )
        self.assertEqual(
            self.client.patch(f'/api/checklists/{item_id}/', {'concluido': True}, format='json').status_code, 200
        )

    def test_comment_author_cannot_be_spoofed(self):
        self.client.force_authenticate(self.member)
        response = self.client.post(
            '/api/comentarios/', {'tarefa': self.task.pk, 'conteudo': 'Real', 'autor': self.other.pk}, format='json'
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['autor'], self.member.pk)
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(f'/api/comentarios/{response.data["id"]}/').status_code, 404)

    def test_material_creator_cannot_be_spoofed(self):
        self.client.force_authenticate(self.member)
        response = self.client.post(
            '/api/materiais-apoio/',
            {'projeto': self.project.pk, 'criador': self.owner.pk, 'titulo': 'Material', 'url': 'https://example.com'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['criador'], self.member.pk)

    def test_user_cannot_elevate_privileges_or_edit_another_account(self):
        response = self.client.patch(
            f'/api/usuarios/{self.owner.pk}/', {'is_superuser': True, 'is_staff': True}, format='json'
        )
        self.assertEqual(response.status_code, 200)
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.is_superuser)
        self.assertFalse(self.owner.is_staff)
        self.assertEqual(
            self.client.patch(f'/api/usuarios/{self.other.pk}/', {'name': 'No'}, format='json').status_code, 404
        )
        self.assertEqual(self.client.delete(f'/api/usuarios/{self.other.pk}/').status_code, 404)

    def test_project_filter_and_pagination(self):
        for i in range(12):
            Tarefa.objects.create(
                projeto=self.project, criador=self.owner, titulo=f'Task {i}', descricao='Real', prioridade=1
            )
        other = Projeto.objects.create(nome='Other', descricao='Real', criado_por=self.owner)
        Tarefa.objects.create(projeto=other, criador=self.owner, titulo='Other', descricao='Real', prioridade=1)
        response = self.client.get('/api/tarefas/', {'projeto': self.project.pk})
        self.assertEqual(response.data['total_pages'], 2)
        self.assertTrue(all(t['projeto'] == self.project.pk for t in response.data['results']))
        self.assertEqual(self.client.get('/api/tarefas/', {'projeto': 'bad'}).status_code, 400)


class ProjectAdminMigrationTests(TransactionTestCase):
    def test_existing_project_gets_creator_membership(self):
        executor = MigrationExecutor(connection)
        before = ('core', '0014_projeto_materialapoio_tarefa_comentario_checklist_and_more')
        after = ('core', '0015_project_creator_membership')
        executor.migrate([before])
        try:
            apps = executor.loader.project_state([before]).apps
            users = apps.get_model('core', 'User')
            owner = users.objects.create(email='migration-owner@test.example')
            other = users.objects.create(email='migration-other@test.example')
            project = apps.get_model('core', 'Projeto').objects.create(nome='Old', descricao='Real', criado_por=owner)
            apps.get_model('core', 'ParticipanteProjeto').objects.create(projeto=project, usuario=other, papel='admin')
            executor = MigrationExecutor(connection)
            executor.migrate([after])
            apps = executor.loader.project_state([after]).apps
            members = apps.get_model('core', 'ParticipanteProjeto')
            self.assertEqual(members.objects.get(projeto_id=project.pk, usuario_id=owner.pk).papel, 'admin')
            self.assertEqual(members.objects.get(projeto_id=project.pk, usuario_id=other.pk).papel, 'admin')
        finally:
            MigrationExecutor(connection).migrate([('core', '0017_tarefa_data_inicio_user_foto')])
