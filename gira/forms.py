from django import forms
from .models import Funcao, Gira, Medium

class LoginPhoneForm(forms.Form):
    celular = forms.CharField(max_length=20)

class GiraForm(forms.ModelForm):
    class Meta:
        model = Gira
        fields = ['titulo','data_hora','linha']

class FuncaoEditForm(forms.ModelForm):
    class Meta:
        model = Funcao
        fields = ['posicao','medium_de_linha','pessoa','status','descricao']
