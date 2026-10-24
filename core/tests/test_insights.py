from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from core.models import Notificacao, ParticipanteProjeto, Projeto, Redistribuicao, Tarefa, User
from core.services.insights import analisar, alertas_sobrecarga


class InsightsTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user('admin@insights.test', 'TestPassword123!')
        self.member = User.objects.create_user('member@insights.test', 'TestPassword123!')
        self.free = User.objects.create_user('free@insights.test', 'TestPassword123!')
        self.other = User.objects.create_user('outsider@insights.test', 'TestPassword123!')
        self.client.force_authenticate(self.admin)
        result = self.client.post('/api/projetos/', {'nome': 'Insights', 'descricao': 'Real'}, format='json')
        self.project = Projeto.objects.get(pk=result.data['id'])
        self.member_link = ParticipanteProjeto.objects.create(projeto=self.project, usuario=self.member, capacidade=5)
        ParticipanteProjeto.objects.create(projeto=self.project, usuario=self.free, capacidade=10)
        self.url = f'/api/projetos/{self.project.pk}/carga-trabalho/'
        self.now = timezone.now()

    def task(self, **kwargs):
        data = dict(projeto=self.project, criador=self.admin, responsavel=self.member,
                    titulo='Atividade', descricao='Real', prioridade=2)
        data.update(kwargs)
        return Tarefa.objects.create(**data)

    def test_weighted_score_deadlines_blocking_and_completed(self):
        self.task(complexidade=3, prioridade=3, prazo=self.now - timedelta(hours=1))  # 7
        self.task(complexidade=2, prazo=self.now + timedelta(hours=48))  # 4
        self.task(complexidade=1, prazo=self.now + timedelta(hours=49))  # 1
        self.task(complexidade=3, impedida=True, prazo=self.now - timedelta(days=1))  # separate
        self.task(situacao='concluida', prioridade=3)
        result = analisar(self.project, self.admin, self.now)
        row = next(p for p in result['participantes'] if p['usuario'] == self.member.pk)
        self.assertEqual((row['pontos'], row['pendentes'], row['bloqueadas']), (12, 4, 1))
        self.assertEqual((row['atrasadas'], row['proximas'], row['altas']), (2, 1, 1))
        self.assertEqual(row['nivel'], 'sobrecarga')

    def test_thresholds_custom_weights_and_capacity(self):
        self.task(complexidade=3)
        self.task(complexidade=1)
        row = analisar(self.project, self.member, self.now)['participantes'][0]
        self.assertEqual(row['nivel'], 'atencao')  # 4 of 5 points
        with override_settings(KANDO_INSIGHTS_PESOS={'baixa': 4}):
            self.assertEqual(analisar(self.project, self.member)['participantes'][0]['pontos'], 7)
        result = self.client.post(f'/api/projetos/{self.project.pk}/capacidade/',
                                  {'usuario': self.member.pk, 'capacidade': 20}, format='json')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(analisar(self.project, self.member)['participantes'][0]['nivel'], 'equilibrada')

    def test_member_only_sees_self_and_cannot_reassign_or_configure(self):
        task = self.task()
        self.client.force_authenticate(self.member)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['administrador'])
        self.assertEqual([p['usuario'] for p in response.data['participantes']], [self.member.pk])
        self.assertEqual(response.data['sugestoes'], [])
        self.assertIsNone(response.data['sem_responsavel'])
        self.assertEqual(self.client.get(f'/api/projetos/{self.project.pk}/sugestoes-redistribuicao/').status_code, 403)
        self.assertEqual(self.client.post(f'/api/projetos/{self.project.pk}/capacidade/',
                         {'usuario': self.member.pk, 'capacidade': 20}, format='json').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/tarefas/{task.pk}/', {'responsavel': self.free.pk}, format='json').status_code, 403)
        self.assertFalse(Redistribuicao.objects.exists())

    def test_outsider_and_anonymous_are_denied(self):
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(self.url).status_code, 401)

    def test_more_than_one_page_is_analysed_and_projects_are_isolated(self):
        for i in range(13):
            self.task(titulo=f'Task {i}')
        private = Projeto.objects.create(nome='Private', descricao='No', criado_por=self.other)
        Tarefa.objects.create(projeto=private, criador=self.other, responsavel=self.member,
                              titulo='Hidden', descricao='No', prioridade=3)
        result = self.client.get(self.url)
        row = next(p for p in result.data['participantes'] if p['usuario'] == self.member.pk)
        self.assertEqual(row['pendentes'], 13)
        self.assertFalse(any(t['titulo'] == 'Hidden' for t in row['tarefas']))

    def test_suggestions_never_auto_assign_or_exceed_target_capacity(self):
        for i in range(6):
            self.task(complexidade=3)
        blocked = self.task(impedida=True)
        result = analisar(self.project, self.admin)
        self.assertTrue(result['sugestoes'])
        rows = {p['usuario']: p for p in result['participantes']}
        received = {}
        for s in result['sugestoes']:
            self.assertNotEqual(s['tarefa'], blocked.pk)
            self.assertNotEqual(s['destino'], s['origem'])
            received[s['destino']] = received.get(s['destino'], 0) + s['pontos']
        for user, points in received.items():
            self.assertLessEqual(rows[user]['pontos'] + points, rows[user]['capacidade'])
        self.assertFalse(Redistribuicao.objects.exists())
        self.assertTrue(all(t.responsavel_id == self.member.pk for t in self.project.tarefas.all()))

    def test_reassignment_logs_and_notifies_both_users_and_checks_stale_state(self):
        task = self.task()
        url = f'/api/tarefas/{task.pk}/'
        before = Notificacao.objects.filter(usuario=self.member).count()
        result = self.client.patch(url, {'responsavel': self.free.pk, 'esperado_responsavel': self.member.pk}, format='json')
        self.assertEqual(result.status_code, 200)
        history = Redistribuicao.objects.get(tarefa=task)
        self.assertEqual((history.anterior_id, history.novo_id, history.autor_id), (self.member.pk, self.free.pk, self.admin.pk))
        self.assertGreater(Notificacao.objects.filter(usuario=self.member).count(), before)
        self.assertTrue(Notificacao.objects.filter(usuario=self.free, tarefa=task, tipo='atribuicao').exists())
        self.assertEqual(self.client.get(url + 'redistribuicoes/').status_code, 200)
        result = self.client.patch(url, {'responsavel': self.admin.pk, 'esperado_responsavel': self.member.pk}, format='json')
        self.assertEqual(result.status_code, 400)
        task.refresh_from_db()
        self.assertEqual(task.responsavel_id, self.free.pk)
        self.assertEqual(Redistribuicao.objects.filter(tarefa=task).count(), 1)

    def test_capacity_rejects_invalid_values_and_outsiders(self):
        url = f'/api/projetos/{self.project.pk}/capacidade/'
        for value in [0, -1, 1001, 'abc']:
            self.assertEqual(self.client.post(url, {'usuario': self.member.pk, 'capacidade': value}, format='json').status_code, 400)
        self.assertEqual(self.client.post(url, {'usuario': self.other.pk, 'capacidade': 10}, format='json').status_code, 400)

    def test_alerts_are_deduplicated_including_soft_deleted_alerts(self):
        for i in range(6):
            self.task()
        alertas_sobrecarga(self.admin)
        alertas_sobrecarga(self.admin)
        self.assertEqual(Notificacao.objects.filter(usuario=self.admin, tipo='sobrecarga').count(), 1)
        Notificacao.objects.filter(tipo='sobrecarga').update(excluida=True)
        alertas_sobrecarga(self.admin)
        self.assertEqual(Notificacao.objects.filter(usuario=self.admin, tipo='sobrecarga').count(), 1)
        alertas_sobrecarga(self.member)
        self.assertFalse(Notificacao.objects.filter(usuario=self.member, tipo='sobrecarga').exists())

    def test_completed_and_blocked_tasks_do_not_generate_false_overload(self):
        for i in range(12):
            self.task(situacao='concluida')
            self.task(impedida=True)
        result = analisar(self.project, self.member)
        self.assertEqual(result['participantes'][0]['pontos'], 0)
        self.assertEqual(result['participantes'][0]['nivel'], 'equilibrada')
