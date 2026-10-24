from django.db import models


class Checklist(models.Model):
    descricao = models.TextField(verbose_name='Descrição do Item do Checklist')
    concluido = models.BooleanField(verbose_name='Concluído', default=False)
    ordem = models.IntegerField(verbose_name='Ordem', default=0)
    tarefa = models.ForeignKey(
        'core.Tarefa',
        on_delete=models.CASCADE,
        related_name='itens_checklist',
        verbose_name='Tarefa'
    )


    class Meta:
        verbose_name = 'Checklist'
        verbose_name_plural = 'Checklists'
        ordering = ['ordem']

    def __str__(self):
        return self.descricao
