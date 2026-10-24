from datetime import timedelta
from uuid import uuid4

from django.utils import timezone

from core.models import Notificacao, Tarefa


def notificar(usuario_id, tipo, mensagem, projeto, tarefa=None, chave=None):
    return Notificacao.objects.get_or_create(
        chave=chave or str(uuid4()),
        defaults=dict(
            usuario_id=usuario_id,
            tipo=tipo,
            titulo=mensagem.split(':')[0][:180],
            mensagem=mensagem,
            projeto=projeto,
            tarefa=tarefa,
        ),
    )


def prazos(usuario=None):
    agora = timezone.now()
    tarefas = (
        Tarefa.objects
        .filter(prazo__lte=agora + timedelta(days=1), responsavel__isnull=False)
        .exclude(situacao='concluida')
        .select_related('projeto')
    )
    if usuario:
        tarefas = tarefas.filter(responsavel=usuario)
    for tarefa in tarefas:
        if not tarefa.projeto.participantes.filter(usuario_id=tarefa.responsavel_id).exists():
            continue
        tipo = 'atraso' if tarefa.prazo < agora else 'prazo'
        texto = 'está atrasada' if tipo == 'atraso' else 'vence nas próximas 24 horas'
        notificar(
            tarefa.responsavel_id,
            tipo,
            f'A tarefa {tarefa.titulo} {texto}, no projeto {tarefa.projeto.nome}.',
            tarefa.projeto,
            tarefa,
            f'{tipo}:{tarefa.pk}:{tarefa.responsavel_id}:{tarefa.prazo.isoformat()}',
        )
