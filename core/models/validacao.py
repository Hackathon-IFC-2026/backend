from django.db import models


class Validacao(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True)
    telefone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(unique=True)
    data_nascimento = models.DateField(blank=True, null=True)
    cnpj = models.CharField(max_length=18, blank=True, null=True)
    data = models.DateField(blank=True, null=True)
    hora = models.TimeField(blank=True, null=True)
    data_hora = models.DateTimeField(blank=True, null=True)
    dia_semana = models.CharField(max_length=10, blank=True, null=True)
    mes = models.CharField(max_length=10, blank=True, null=True)
    ano = models.CharField(max_length=4, blank=True, null=True)
    cep = models.CharField(max_length=9, blank=True, null=True)
    rua = models.CharField(max_length=100, blank=True, null=True)
    complemento = models.CharField(max_length=100, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=100, blank=True, null=True)
    numero = models.CharField(max_length=10, blank=True, null=True)
    pais = models.CharField(max_length=100, blank=True, null=True)
    titulo = models.CharField(max_length=100, blank=True, null=True)
    descricao = models.TextField(blank=True, null=True)
    observacao = models.TextField(blank=True, null=True)
    ativo = models.BooleanField(default=True)
    inativo = models.BooleanField(default=False)
    foto = models.ImageField(upload_to='validacoes/', blank=True, null=True)
    status = models.CharField(max_length=20, blank=True, null=True)
    quantidade = models.IntegerField(blank=True, null=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    percentual = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    peso = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    medida = models.CharField(max_length=20, blank=True, null=True)
    nota = models.DecimalField(max_digits=3, decimal_places=1, blank=True, null=True)
    avaliacao = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = 'Validação'
        verbose_name_plural = 'Validações'

    def __str__(self):
        return self.nome
