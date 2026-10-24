from django.db import models


class ParticipanteProjeto(models.Model):
    class Papel(models.TextChoices):
        ADMIN = 'admin', 'Administrador'
        PARTICIPANTE = 'participante', 'Participante'

    entrou_em = models.DateTimeField(auto_now_add=True, verbose_name='Entrou em')
    papel = models.CharField(
        max_length=20, choices=Papel.choices, default=Papel.PARTICIPANTE, verbose_name='Papel do Participante'
    )
    projeto = models.ForeignKey(
        'core.Projeto', on_delete=models.CASCADE, related_name='participantes', verbose_name='Projeto'
    )
    usuario = models.ForeignKey(
        'core.User', on_delete=models.CASCADE, related_name='projetos_participados', verbose_name='Usuário'
    )

    class Meta:
        verbose_name = 'Participante do Projeto'
        verbose_name_plural = 'Participantes dos Projetos'
        ordering = ['entrou_em']
        constraints = [
            models.UniqueConstraint(
                fields=['projeto', 'usuario'],
                name='participante_unico_por_projeto'
            )
        ]

    def __str__(self):
        return f'{self.usuario} - {self.projeto}'
