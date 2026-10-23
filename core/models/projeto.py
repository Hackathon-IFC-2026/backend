from django.db import models


class Projeto(models.Model):
    nome = models.CharField(max_length=100, verbose_name='Nome do Projeto')
    descricao = models.TextField(verbose_name='Descrição do Projeto')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    atualizado_em = models.DateTimeField(auto_now=True, verbose_name='Atualizado em')
    criador = models.ForeignKey(
        'core.User', on_delete=models.CASCADE, related_name='projetos_criados', verbose_name='Criador do Projeto'
    )

    class Meta:
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'

    def __str__(self):
        return self.nome
