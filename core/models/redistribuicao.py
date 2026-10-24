from django.conf import settings
from django.db import models


class Redistribuicao(models.Model):
    tarefa = models.ForeignKey('core.Tarefa', on_delete=models.CASCADE, related_name='redistribuicoes')
    anterior = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    novo = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criada_em', '-id']
