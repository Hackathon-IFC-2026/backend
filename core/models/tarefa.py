from django.db import models

from django.utils import timezone


class Tarefa(models.Model):
    class Situacao(models.TextChoices):
        EM_ABERTO = 'aberta', 'Em aberto'
        EM_ANDAMENTO = 'andamento', 'Em andamento'
        CONCLUIDA = 'concluida', 'Concluída'

    class Prioridade(models.IntegerChoices):
        BAIXA = 1, 'Baixa'
        MEDIA = 2, 'Média'
        ALTA = 3, 'Alta'

    titulo = models.CharField(max_length=100, verbose_name='Título da Tarefa')
    descricao = models.TextField(verbose_name='Descrição da Tarefa')
    prazo = models.DateTimeField(null=True, blank=True, verbose_name='Prazo')
    situacao = models.CharField(
        max_length=20, choices=Situacao.choices, default=Situacao.EM_ABERTO, verbose_name='Situação'
    )
    concluida_em = models.DateTimeField(null=True, blank=True, verbose_name='Concluída em')
    criada_em = models.DateTimeField(auto_now_add=True, verbose_name='Criada em')
    atualizada_em = models.DateTimeField(auto_now=True, verbose_name='Atualizada em')
    posicao = models.IntegerField(default=0, verbose_name='Posição')
    prioridade = models.IntegerField(
        choices=Prioridade.choices,
        verbose_name='Prioridade'
    )
    projeto = models.ForeignKey(
        'core.Projeto', on_delete=models.CASCADE, related_name='tarefas', verbose_name='Projeto'
    )
    criador = models.ForeignKey(
        'core.User', on_delete=models.PROTECT, related_name='tarefas_criadas', verbose_name='Criador'
    )
    responsavel = models.ForeignKey(
        'core.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tarefas_responsaveis',
        verbose_name='Responsável',
    )

    @property
    def atrasada(self):
        return (
            self.prazo is not None
            and self.prazo < timezone.now()
            and self.situacao != self.Situacao.CONCLUIDA
        )

    @property
    def bloqueada(self):
        return self.responsavel is None

    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'

    def __str__(self):
        return self.titulo
