from django.db import models


class Checklist(models.Model):
    descricao = models.TextField(verbose_name='Descrição do Projeto')
    concluido = models.tinyint(verbose_name='Concluído', default=0)
    ordem = models.IntegerField(verbose_name='Ordem', default=0)


    class Meta:
        verbose_name = 'Checklist'
        verbose_name_plural = 'Checklists'

    def __str__(self):
        return self.nome
