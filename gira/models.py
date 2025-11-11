from django.db import models
from django.utils import timezone


# ⚠️ NÃO ALTERADO — já está correto e vinculado à tabela gira_user
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

    USERNAME_FIELD = 'celular'
    REQUIRED_FIELDS = []

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    class Meta:
        db_table = 'gira_user'

    def __str__(self):
        return f"{self.nome} ({self.celular})"
        
    @property
    def medium(self):
        """Retorna o médium associado a este usuário, se houver"""
        from .models import Medium
        return Medium.objects.filter(user_id=self.id).first()


# ✅ ajustado para refletir a tabela gira_medium
class Medium(models.Model):
    nome = models.CharField(max_length=150)
    habilitado = models.BooleanField(default=True)
    user = models.OneToOneField('User', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        db_table = 'gira_medium'

    def __str__(self):
        return self.nome


# ✅ ajustado com db_table correto
class CambonePool(models.Model):
    nome = models.CharField(max_length=150)
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'gira_cambonepool'

    def __str__(self):
        return f"{self.ordem} - {self.nome}"


# ✅ ajustado conforme gira_gira (schema real)
class Gira(models.Model):
    titulo = models.CharField(max_length=200)
    data_hora = models.DateTimeField()
    linha = models.CharField(max_length=150)
    status = models.CharField(max_length=50, default='Ativa')
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        db_table = 'gira_gira'

    def __str__(self):
        return f"{self.titulo} ({self.linha}) - {self.data_hora:%d/%m/%Y %H:%M}"


# ✅ atualizado conforme tabela gira_funcao (colunas e nomes reais)
class Funcao(models.Model):
    gira = models.ForeignKey(Gira, on_delete=models.CASCADE, related_name='funcoes')
    chave = models.CharField(max_length=50)
    tipo = models.CharField(max_length=50)  # "Cambone", "Organização", "Limpeza"
    posicao = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=50, default='Vaga')
    descricao = models.TextField(blank=True)
    medium_de_linha = models.ForeignKey(Medium, on_delete=models.SET_NULL, null=True, blank=True)
    pessoa = models.ForeignKey('Medium', null=True, blank=True, on_delete=models.SET_NULL, related_name='funcoes_assumidas')


    class Meta:
        db_table = 'gira_funcao'

    @property
    def medium_nome(self):
        """Retorna o nome do médium de linha (da tabela gira_medium)."""
        return self.medium_de_linha.nome if self.medium_de_linha else None

    @property
    def pessoa_nome(self):
        """Retorna o nome do usuário que assumiu a função (da tabela gira_user)."""
        return self.pessoa.nome if self.pessoa else None


    def __str__(self):
        return f"{self.tipo} - {self.posicao or ''} - {self.status}"
        
    @property
    def nome_responsavel(self):
        """Nome do médium responsável pela função, ou '—' se vaga."""
        if self.pessoa and self.pessoa.medium:
            return self.pessoa.medium.nome
        elif self.pessoa:
            return self.pessoa.nome
        return "—"


# ✅ atualizado conforme gira_historico (colunas reais)
class Historico(models.Model):
    gira = models.ForeignKey(Gira, on_delete=models.CASCADE)
    funcao = models.ForeignKey(Funcao, on_delete=models.SET_NULL, null=True)
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    acao = models.CharField(max_length=50)
    data = models.DateTimeField(default=timezone.now)
    info = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = 'gira_historico'

    def __str__(self):
        return f"{self.data:%d/%m/%Y %H:%M} - {self.acao}"
