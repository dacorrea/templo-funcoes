from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Users, Gira, Funcao

def login_view(request):
    """Login apenas por número de celular."""
    if request.method == 'POST':
        celular = ''.join(ch for ch in request.POST.get('celular', '') if ch.isdigit())

        try:
            # Busca o usuário diretamente na tabela Users
            user = Users.objects.get(telefone=celular, ativo=True)
        except Users.DoesNotExist:
            messages.error(request, 'Celular não encontrado ou usuário inativo.')
            return render(request, 'gira/login.html')

        # Guarda dados mínimos na sessão
        request.session['user_id'] = user.id
        request.session['user_nome'] = user.nome
        request.session['user_telefone'] = user.telefone

        # Redireciona para a lista de funções
        return redirect('gira:lista_funcoes')

    return render(request, 'gira/login.html')


def _get_user(request):
    """Retorna o usuário da sessão atual."""
    uid = request.session.get('user_id')
    if not uid:
        return None
    try:
        return Users.objects.get(id=uid)
    except Users.DoesNotExist:
        return None


def lista_funcoes(request):
    """Lista de funções da última gira."""
    user = _get_user(request)
    if not user:
        return redirect('gira:login')

    gira = Gira.objects.order_by('-data_hora').first()
    if not gira:
        messages.info(request, 'Nenhuma gira cadastrada.')
        return render(request, 'gira/lista_funcoes.html', {'user': user})

    funcoes = gira.funcoes.all().order_by('tipo', 'posicao')
    cambones = funcoes.filter(tipo='Cambones')
    organizacao = funcoes.filter(tipo='Organizacao')
    limpeza = funcoes.filter(tipo='Limpeza')

    return render(request, 'gira/lista_funcoes.html', {
        'user': user, 'gira': gira,
        'cambones': cambones, 'organizacao': organizacao, 'limpeza': limpeza
    })
