from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

# Gerenciador customizado para criar usuários com celular
class UserManager(BaseUserManager):
    def create_user(self, celular, password=None, **extra_fields):
        if not celular:
            raise ValueError('O campo celular é obrigatório.')
        user = self.model(celular=celular, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, celular, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(celular, password, **extra_fields)

# Modelo principal de usuário
class User(AbstractBaseUser, PermissionsMixin):
    celular = models.CharField(max_length=15, unique=True)
    nome = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = 'celular'
    REQUIRED_FIELDS = []  # só o celular é obrigatório

    objects = UserManager()

    def __str__(self):
        return self.celular

# Caso você queira manter perfis adicionais
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    foto = models.ImageField(upload_to='fotos/', blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.user.celular



# ----------- DEMAIS MODELOS -----------
class Medium(models.Model):
    nome = models.CharField(max_length=150)
    habilitado = models.BooleanField(default=True)
    def __str__(self):
        return self.nome


class CambonePool(models.Model):
    nome = models.CharField(max_length=150)
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    def __str__(self):
        return self.nome


class Gira(models.Model):
    titulo = models.CharField(max_length=200)
    data_hora = models.DateTimeField()
    linha = models.CharField(max_length=150)
    criado_por = models.ForeignKey(UserProfile, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, default='ativa')

    def __str__(self):
        return f"{self.titulo} - {self.linha} - {self.data_hora}"


class Funcao(models.Model):
    TIPO = (('Cambones', 'Cambones'), ('Organizacao', 'Organizacao'), ('Limpeza', 'Limpeza'))
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
