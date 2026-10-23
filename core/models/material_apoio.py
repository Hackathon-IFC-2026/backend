from django.db import models


class MaterialApoio(models.Model):
    titulo = models.CharField(max_length=100, verbose_name='Título do Material de Apoio')
    url = models.URLField(verbose_name='URL do Material de Apoio')
    criado_em = models.DateTimeField(auto_now_add=True, verbose_name='Criado em')
    projeto = models.ForeignKey(
        'core.Projeto',
        on_delete=models.CASCADE,
        related_name='materiais_apoio',
        verbose_name='Projeto'
    )
    criador = models.ForeignKey(
        'core.User',
        on_delete=models.PROTECT,
        related_name='materiais_criados',
        verbose_name='Criador'
    )

    class Meta:
        verbose_name = 'Material de Apoio'
        verbose_name_plural = 'Materiais de Apoio'
        ordering = ['criado_em']

    def __str__(self):
        return self.titulo
