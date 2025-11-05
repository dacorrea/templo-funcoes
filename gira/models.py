from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    nome = models.CharField(max_length=150)
    celular = models.CharField(max_length=20, unique=True)
    role = models.CharField(max_length=10, choices=(('admin','admin'),('user','user')), default='user')
    ativo = models.BooleanField(default=True)

    def __str__(self):
        return self.nome

class Medium(models.Model):
    nome = models.CharField(max_length=150)
    habilitado = models.BooleanField(default=True)
    def __str__(self): return self.nome

class CambonePool(models.Model):
    nome = models.CharField(max_length=150)
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    def __str__(self): return self.nome

class Gira(models.Model):
    titulo = models.CharField(max_length=200)
    data_hora = models.DateTimeField()
    linha = models.CharField(max_length=150)
    criado_por = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='ativa')

    def __str__(self):
        return f"{self.titulo} - {self.linha} - {self.data_hora}"

class Funcao(models.Model):
    TIPO = (('Cambones','Cambones'),('Organizacao','Organizacao'),('Limpeza','Limpeza'))
    gira = models.ForeignKey(Gira, on_delete=models.CASCADE, related_name='funcoes')
    chave = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=TIPO)
    posicao = models.CharField(max_length=50, blank=True)
    medium_de_linha = models.ForeignKey(Medium, on_delete=models.SET_NULL, null=True, blank=True)
    pessoa = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='Vaga')
    descricao = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.posicao} - {self.status}"

class Historico(models.Model):
    gira = models.ForeignKey(Gira, on_delete=models.CASCADE)
    funcao = models.ForeignKey(Funcao, on_delete=models.SET_NULL, null=True)
    usuario = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=50)
    data = models.DateTimeField(auto_now_add=True)
    info = models.JSONField(null=True, blank=True)
