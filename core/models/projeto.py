from django.db import models


class Projeto(models.Model):
    class Situacao(models.TextChoices):
        EM_ABERTO = 'aberta', 'Em aberto'
        EM_ANDAMENTO = 'andamento', 'Em andamento'
        CONCLUIDA = 'concluida', 'Concluída'
    nome = models.CharField(max_length=100, verbose_name='Nome do Projeto')
    descricao = models.TextField(verbose_name='Descrição do Projeto')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    criado_por = models.ForeignKey(
        'core.User', on_delete=models.PROTECT, related_name='projetos_criados', verbose_name='Criador do Projeto'
    )
    situacao = models.CharField(
        max_length=20, choices=Situacao.choices, default=Situacao.EM_ABERTO, verbose_name='Situação'
    )

    class Meta:
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'

    def __str__(self):
        return self.nome
