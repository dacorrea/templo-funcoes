from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Gira, Funcao
from django.http import JsonResponse
from django.contrib.auth import get_user_model
from .models import User



def check_user_model(request):
    User = get_user_model()
    return JsonResponse({
        "auth_user_model": str(User),
        "db_table": User._meta.db_table,
        "fields": [f.name for f in User._meta.fields],
    })


def login_view(request):
    from django.contrib.auth import get_user_model  # <-- mover para dentro
    User = get_user_model()
    if request.method == 'POST':
        celular = ''.join(ch for ch in request.POST.get('celular', '') if ch.isdigit())

        try:
            # Busca o usuário diretamente na tabela gira_user
            user = User.objects.get(celular=celular, is_active=True)
        except User.DoesNotExist:
            messages.error(request, 'Celular não encontrado ou usuário inativo.')
            return render(request, 'gira/login.html')

        # Guarda dados mínimos na sessão
        request.session['user_id'] = user.id
        request.session['user_nome'] = user.nome
        request.session['user_telefone'] = user.celular

        # Redireciona para a lista de funções
        return redirect('gira:lista_funcoes')

    return render(request, 'gira/login.html')


def _get_user(request):
    """Retorna o usuário da sessão atual."""
    uid = request.session.get('user_id')
    if not uid:
        return None
    try:
        return User.objects.get(id=uid)
    except User.DoesNotExist:
        return None


def lista_funcoes(request):
    """Lista de funções da última gira, agrupadas por tipo (compatível com o layout atual)."""
    user = _get_user(request)
    if not user:
        return redirect('gira:login')

    gira = Gira.objects.order_by('-data_hora').first()
    if not gira:
        messages.info(request, 'Nenhuma gira cadastrada.')
        return render(request, 'gira/lista_funcoes.html', {'user': user})

    # Busca todas as funções da gira, incluindo medium e pessoa
    funcoes = gira.funcoes.select_related('medium_de_linha', 'pessoa').all()

    # ✅ Normaliza os nomes dos tipos (tratando variações Cambone/Cambones, Organização/Organizacao, etc.)
    cambones = [f for f in funcoes if f.tipo.lower().startswith('cambone')]
    organizacao = [f for f in funcoes if f.tipo.lower().startswith('organ')]
    limpeza = [f for f in funcoes if f.tipo.lower().startswith('limp')]

    context = {
        'user': user,
        'gira': gira,
        'cambones': cambones,
        'organizacao': organizacao,
        'limpeza': limpeza,
    }
    return render(request, 'gira/lista_funcoes.html', context)





def logout_view(request):
    """Finaliza a sessão do usuário e redireciona para o login."""
    request.session.flush()
    return redirect('gira:login')

