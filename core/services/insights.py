"""Deterministic workload estimates. Never an individual performance score."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.project_permissions import administra


def analisar(projeto, usuario, agora=None):
    agora = agora or timezone.now()
    pesos = {'baixa': 1, 'media': 2, 'alta': 3, 'proxima': 2, 'atrasada': 3, 'prioridade': 1,
             **getattr(settings, 'KANDO_INSIGHTS_PESOS', {})}
    atencao = getattr(settings, 'KANDO_INSIGHTS_ATENCAO', 0.8)
    admin = administra(projeto, usuario)
    membros = projeto.participantes.select_related('usuario').filter(usuario__is_active=True)
    # Do not calculate or return colleagues' workloads for ordinary members.
    if not admin:
        membros = membros.filter(usuario=usuario)
    tarefas = list(projeto.tarefas.exclude(situacao='concluida').order_by('id'))
    linhas = []
    for membro in membros:
        items = []
        for tarefa in tarefas:
            if tarefa.responsavel_id != membro.usuario_id:
                continue
            atrasada = bool(tarefa.prazo and tarefa.prazo < agora)
            proxima = bool(tarefa.prazo and agora <= tarefa.prazo <= agora + timedelta(hours=48))
            pontos = pesos[{1: 'baixa', 2: 'media', 3: 'alta'}[tarefa.complexidade]]
            pontos += pesos['atrasada'] if atrasada else pesos['proxima'] if proxima else 0
            pontos += pesos['prioridade'] if tarefa.prioridade == 3 else 0
            # Blocked work stays visible but is separated from executable workload.
            items.append(dict(id=tarefa.pk, titulo=tarefa.titulo, situacao=tarefa.situacao,
                              prioridade=tarefa.prioridade, prazo=tarefa.prazo,
                              complexidade=tarefa.complexidade, impedida=tarefa.impedida,
                              atrasada=atrasada, proxima=proxima, pontos=pontos))
        capacidade = max(1, membro.capacidade)
        pontos = sum(t['pontos'] for t in items if not t['impedida'])
        nivel = 'sobrecarga' if pontos > capacidade else 'atencao' if pontos >= capacidade * atencao else 'equilibrada'
        linhas.append(dict(usuario=membro.usuario_id, vinculo=membro.pk,
                           nome=membro.usuario.name or membro.usuario.email, papel=membro.papel,
                           capacidade=capacidade, pontos=pontos, percentual=round(pontos / capacidade * 100),
                           nivel=nivel, pendentes=len(items),
                           andamento=sum(t['situacao'] == 'andamento' for t in items),
                           atrasadas=sum(t['atrasada'] for t in items),
                           proximas=sum(t['proxima'] for t in items),
                           altas=sum(t['prioridade'] == 3 for t in items),
                           bloqueadas=sum(t['impedida'] for t in items), tarefas=items))
    sugestoes = []
    # Simulate the combined effect of suggestions to avoid overloading a recipient.
    simulacao = {p['usuario']: p['pontos'] for p in linhas}
    if admin:
        for origem in sorted(linhas, key=lambda p: p['percentual'], reverse=True):
            if origem['nivel'] != 'sobrecarga':
                continue
            for tarefa in sorted(origem['tarefas'], key=lambda t: (t['atrasada'], t['proxima'], t['prioridade'], t['pontos'], t['id'])):
                if simulacao[origem['usuario']] <= origem['capacidade']:
                    break
                if tarefa['impedida']:
                    continue
                candidatos = [p for p in linhas if p['usuario'] != origem['usuario']
                              and simulacao[p['usuario']] + tarefa['pontos'] <= p['capacidade']
                              and (simulacao[p['usuario']] + tarefa['pontos']) / p['capacidade']
                              < simulacao[origem['usuario']] / origem['capacidade']]
                if not candidatos:
                    continue
                destino = min(candidatos, key=lambda p: (simulacao[p['usuario']] / p['capacidade'], p['usuario']))
                sugestoes.append(dict(tarefa=tarefa['id'], titulo=tarefa['titulo'], origem=origem['usuario'],
                                     destino=destino['usuario'], pontos=tarefa['pontos'],
                                     motivo='Menor carga estimada e capacidade disponível para esta atividade.'))
                simulacao[origem['usuario']] -= tarefa['pontos']
                simulacao[destino['usuario']] += tarefa['pontos']
    return dict(projeto=projeto.pk, administrador=admin, calculado_em=agora, participantes=linhas,
                sugestoes=sugestoes, pesos=pesos, limite_atencao=atencao,
                sem_responsavel=sum(t.responsavel_id is None for t in tarefas) if admin else None)


def alertas_sobrecarga(usuario):
    from hashlib import sha256
    import json
    from core.models import Projeto
    from core.services.notificacoes import notificar
    projetos = Projeto.objects.filter(participantes__usuario=usuario, participantes__papel='admin').distinct()
    for projeto in projetos:
        resultado = analisar(projeto, usuario)
        for pessoa in resultado['participantes']:
            if pessoa['nivel'] != 'sobrecarga':
                continue
            estado = json.dumps({'capacidade': pessoa['capacidade'], 'tarefas': pessoa['tarefas']}, default=str, sort_keys=True)
            assinatura = sha256(estado.encode()).hexdigest()
            notificar(usuario.pk, 'sobrecarga',
                      f"Possível sobrecarga: {pessoa['nome']} tem {pessoa['pendentes']} tarefas pendentes "
                      f"e {pessoa['proximas']} com prazo em até 48h, no projeto {projeto.nome}. Analisar distribuição no Kando Insights.",
                      projeto, chave=f'insights:{projeto.pk}:{usuario.pk}:{pessoa["usuario"]}:{assinatura}')
