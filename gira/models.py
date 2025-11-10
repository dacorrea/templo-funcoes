from django.db import models
from django.utils import timezone

class User(models.Model):
    password = models.CharField(max_length=128, null=True, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    is_superuser = models.BooleanField(default=False)
    username = models.CharField(max_length=150, unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    celular = models.CharField(max_length=15, unique=True)
    nome = models.CharField(max_length=150)
    email = models.EmailField(null=True, blank=True)

     # ✅ Campos necessários para funcionar como modelo de usuário
    USERNAME_FIELD = 'celular'
    REQUIRED_FIELDS = []  # ou [] se preferir que só o celular seja obrigatório

    class Meta:
        db_table = 'gira_user'  # usa a tabela existente

    def __str__(self):
        return f"{self.nome} ({self.celular})"


class Medium(models.Model):
    nome = models.CharField(max_length=150)
    habilitado = models.BooleanField(default=True)
    is_linha = models.BooleanField(default=False)  # ✅ define se é médium de linha

    def __str__(self):
        return self.nome


class Gira(models.Model):
    titulo = models.CharField(max_length=200)
    data_hora = models.DateTimeField()
    linha = models.CharField(max_length=150)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='ativa')

    def __str__(self):
        return f"{self.titulo} - {self.linha} ({self.data_hora.strftime('%d/%m/%Y')})"


class Funcao(models.Model):
    TIPO = (
        ('Cambones', 'Cambones'),
        ('Organizacao', 'Organização'),
        ('Limpeza', 'Limpeza'),
    )
    gira = models.ForeignKey(Gira, on_delete=models.CASCADE, related_name='funcoes')
    chave = models.CharField(max_length=50)
    tipo = models.CharField(max_length=20, choices=TIPO)
    posicao = models.CharField(max_length=50, blank=True)
    medium_de_linha = models.ForeignKey(Medium, on_delete=models.SET_NULL, null=True, blank=True, related_name='funcoes_linha')
    pessoa = models.ForeignKey(Medium, on_delete=models.SET_NULL, null=True, blank=True, related_name='funcoes_pessoa')
    status = models.CharField(max_length=20, default='Vaga')
    descricao = models.TextField(blank=True)

    def __str__(self):
        return f"{self.tipo} - {self.posicao} ({self.status})"


class Historico(models.Model):
    gira = models.ForeignKey(Gira, on_delete=models.CASCADE)
    funcao = models.ForeignKey(Funcao, on_delete=models.SET_NULL, null=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=50)
    data = models.DateTimeField(auto_now_add=True)
    info = models.JSONField(null=True, blank=True)
