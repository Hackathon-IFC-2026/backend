from django.conf import settings
from django.db import models


class Notificacao(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notificacoes')
    projeto = models.ForeignKey('core.Projeto', null=True, on_delete=models.SET_NULL)
    tarefa = models.ForeignKey('core.Tarefa', null=True, on_delete=models.SET_NULL)
    tipo = models.CharField(max_length=40)
    titulo = models.CharField(max_length=180)
    mensagem = models.TextField()
    lida = models.BooleanField(default=False)
    excluida = models.BooleanField(default=False)
    criada_em = models.DateTimeField(auto_now_add=True)
    chave = models.CharField(max_length=255, unique=True)

    class Meta:
        ordering = ['-criada_em', '-id']
