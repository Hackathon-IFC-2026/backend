from django.db import models


class Tarefa(models.Model):
    titulo = models.CharField(max_length=100, verbose_name='Título da Tarefa')
    descricao = models.TextField(verbose_name='Descrição da Tarefa')
    prioridade = models.IntegerField(verbose_name='Prioridade', default=0)
    prazo = models.DateTimeField(verbose_name='Prazo', null=True, blank=True)
    situacao = models.CharField(max_length=20, verbose_name='Situação', default='pendente')
    concluida_em = models.DateTimeField(verbose_name='Concluída em', null=True, blank=True)
    criada_em = models.DateTimeField(auto_now_add=True, verbose_name='Criada em')
    atualizada_em = models.DateTimeField(auto_now=True, verbose_name='Atualizada em')
    posicao = models.IntegerField(verbose_name='Posição', default=0)
    

    class Meta:
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'

    def __str__(self):
        return self.nome
