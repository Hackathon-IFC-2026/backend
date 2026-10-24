from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

from core.models import ParticipanteProjeto, Tarefa
from core.services.notificacoes import notificar


@receiver(pre_save, sender=Tarefa)
def antes_tarefa(sender, instance, **kwargs):
    instance._antes = (
        sender.objects
        .filter(pk=instance.pk)
        .values('titulo', 'descricao', 'prioridade', 'complexidade', 'impedida', 'data_inicio', 'prazo', 'situacao', 'responsavel_id')
        .first()
    )


@receiver(post_save, sender=Tarefa)
def tarefa_salva(sender, instance, created, **kwargs):
    anterior = getattr(instance, '_antes', None)
    projeto = instance.projeto
    if instance.responsavel_id:
        atribuida = created or not anterior or anterior['responsavel_id'] != instance.responsavel_id
        alterada = anterior and any(anterior[k] != getattr(instance, k) for k in anterior)
        if atribuida or alterada:
            tipo = 'atribuicao' if atribuida else 'alteracao'
            texto = 'Você recebeu uma nova tarefa' if atribuida else 'Sua tarefa foi atualizada'
            notificar(
                instance.responsavel_id,
                tipo,
                f'{texto}: {instance.titulo}, no projeto {projeto.nome}.',
                projeto,
                instance,
            )
    if instance.situacao == 'concluida' and (created or anterior and anterior['situacao'] != 'concluida'):
        for usuario_id in projeto.participantes.filter(papel='admin').values_list('usuario_id', flat=True):
            notificar(
                usuario_id,
                'conclusao',
                f'Tarefa concluída: {instance.titulo}, no projeto {projeto.nome}.',
                projeto,
                instance,
            )


@receiver(pre_save, sender=ParticipanteProjeto)
def antes_participacao(sender, instance, **kwargs):
    instance._papel_antes = sender.objects.filter(pk=instance.pk).values_list('papel', flat=True).first()


@receiver(post_save, sender=ParticipanteProjeto)
def participacao_salva(sender, instance, created, **kwargs):
    anterior = getattr(instance, '_papel_antes', None)
    if created:
        notificar(
            instance.usuario_id,
            'participacao',
            f'Você foi adicionado ao projeto {instance.projeto.nome}.',
            instance.projeto,
        )
    elif anterior != instance.papel:
        papel = 'administrador' if instance.papel == 'admin' else 'participante'
        notificar(
            instance.usuario_id,
            'permissao',
            f'Sua função no projeto {instance.projeto.nome} foi alterada para {papel}.',
            instance.projeto,
        )


@receiver(post_delete, sender=ParticipanteProjeto)
def participacao_removida(sender, instance, **kwargs):
    origin = kwargs.get('origin')
    if not isinstance(origin, ParticipanteProjeto) and getattr(origin, 'model', None) is not ParticipanteProjeto:
        return
    if instance.projeto_id and instance.projeto.__class__.objects.filter(pk=instance.projeto_id).exists():
        notificar(
            instance.usuario_id, 'remocao', f'Você foi removido do projeto {instance.projeto.nome}.', instance.projeto
        )
