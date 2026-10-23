from django.db import models


class Comentario(models.Model):
    conteudo = models.TextField(verbose_name='Conteúdo do Comentário')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    tarefa = models.ForeignKey(
        'core.Tarefa',
        on_delete=models.CASCADE,
        related_name='comentarios',
        verbose_name='Tarefa'
    )
    autor = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        related_name='comentarios',
        verbose_name='Autor'
    )

    class Meta:
        verbose_name = 'Comentário'
        verbose_name_plural = 'Comentários'
        ordering = ['criado_em']

    def __str__(self):
        return self.conteudo
