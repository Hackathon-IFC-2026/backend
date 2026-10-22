from django.db import models


class Validacao(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14, unique=True)
    telefone = models.CharField(max_length=15, null=True, blank=True)
    email = models.EmailField(unique=True)
    data_nascimento = models.DateField(null=True, blank=True)
    cnpj = models.CharField(max_length=18, null=True, blank=True)
    data = models.DateField(null=True, blank=True)
    hora = models.TimeField(null=True, blank=True)
    data_hora = models.DateTimeField(null=True, blank=True)
    dia_semana = models.CharField(max_length=10, null=True, blank=True)
    mes = models.CharField(max_length=10, null=True, blank=True)
    ano = models.CharField(max_length=4, null=True, blank=True)
    cep = models.CharField(max_length=9, null=True, blank=True)
    rua = models.CharField(max_length=100, null=True, blank=True)
    complemento = models.CharField(max_length=100, null=True, blank=True)
    bairro = models.CharField(max_length=100, null=True, blank=True)
    cidade = models.CharField(max_length=100, null=True, blank=True)
    estado = models.CharField(max_length=100, null=True, blank=True)
    numero = models.CharField(max_length=10, null=True, blank=True)
    pais = models.CharField(max_length=100, null=True, blank=True)
    titulo = models.CharField(max_length=100, null=True, blank=True)
    descricao = models.TextField(null=True, blank=True)
    observacao = models.TextField(null=True, blank=True)
    ativo = models.BooleanField(default=True)
    inativo = models.BooleanField(default=False)
    foto = models.ImageField(upload_to='validacoes/', null=True, blank=True)
    status = models.CharField(max_length=20, null=True, blank=True)
    quantidade = models.IntegerField(null=True, blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    percentual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    peso = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    medida = models.CharField(max_length=20, null=True, blank=True)
    nota = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    avaliacao = models.TextField(null=True, blank=True)


    class Meta:
        verbose_name = 'Validação'
        verbose_name_plural = 'Validações'

    def __str__(self):
        return self.nome