from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Gira, Funcao, Medium, Historico
from django.contrib.auth import get_user_model
from .models import User
from django.utils import timezone

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


def _display_name_for_person(funcao):
    """
    Retorna o nome a exibir para a pessoa associada à função.
    1) Se existe pessoa (gira_user), usa pessoa.nome
    2) Se pessoa está vazia e existe medium_de_linha com nome, tenta usar medium_de_linha.nome
    3) Fallback: '-' 
    """
    # 1) pessoa (usuário)
    if getattr(funcao, 'pessoa', None):
        nome = getattr(funcao.pessoa, 'nome', None)
        if nome and nome.strip():
            return nome.strip()
    # 2) talvez a pessoa foi salva como referência direta a um medium (fallback)
    if getattr(funcao, 'medium_de_linha', None):
        nome_med = getattr(funcao.medium_de_linha, 'nome', None)
        if nome_med and nome_med.strip():
            return nome_med.strip()
    # 3) fallback
    return '-'

def lista_funcoes(request):
    """Lista de funções da última gira, agrupadas e ordenadas."""
    user = _get_user(request)
    if not user:
        return redirect('gira:login')

    gira = Gira.objects.order_by('-data_hora').first()
    if not gira:
        messages.info(request, 'Nenhuma gira cadastrada.')
        return render(request, 'gira/lista_funcoes.html', {'user': user})

    # Carrega funções com joins para evitar N+1
    funcoes = list(gira.funcoes.select_related('medium_de_linha', 'pessoa').all())

    # Define ordem específica para os grupos
    ordem_organizacao = ["Portão", "Distribuir senha", "Lojinha", "Chamar senha"]

    # Agrupamentos
    cambones = []
    organizacao = []
    limpeza = []

    for f in funcoes:
        tipo = (f.tipo or '').lower()
        chave = (f.chave or '').lower()
        descricao = (f.descricao or '').lower()

        # Identifica Cambones
        if 'cambone' in tipo or 'cambone' in chave or 'cambone' in descricao:
            cambones.append(f)
        # Organização
        elif any(pal.lower() in descricao for pal in ordem_organizacao):
            organizacao.append(f)
        # Limpeza
        elif 'limp' in tipo or 'limp' in chave or 'limp' in descricao:
            limpeza.append(f)
        else:
            organizacao.append(f)

    # Ordena Cambones por nome do médium (alfabético, "Mãe Bruna" primeiro)
    cambones.sort(key=lambda x: ('' if (x.medium_de_linha and x.medium_de_linha.nome.lower() == 'mãe bruna') else x.medium_de_linha.nome if x.medium_de_linha else 'zzzz'))

    # Ordena Organização conforme ordem pré-definida
    organizacao.sort(key=lambda x: ordem_organizacao.index(x.descricao) if x.descricao in ordem_organizacao else 99)

    # Ordena Limpeza por nome (ou posicao se houver)
    limpeza.sort(key=lambda x: x.posicao or '')

    context = {
        'user': user,
        'gira': gira,
        'cambones': cambones,
        'organizacao': organizacao,
        'limpeza': limpeza,
        'ordem_organizacao': ordem_organizacao,  # 🔹 envia lista pro template
    }

    return render(request, 'gira/lista_funcoes.html', context)



    # Prepara objetos simples para o template (com nome exibível)
    def prepare_list(lst):
        out = []
        for f in lst:
            out.append({
                'id': f.id,
                'chave': f.chave,
                'tipo': f.tipo,
                'posicao': f.posicao or '',
                'status': f.status,
                'descricao': f.descricao or '',
                'medium_nome': (f.medium_de_linha.nome if f.medium_de_linha else ''),
                'pessoa_nome': _display_name_for_person(f),
            })
        return out

    context = {
        'user': user,
        'gira': gira,
        'cambones': prepare_list(cambones),
        'organizacao': prepare_list(organizacao),
        'limpeza': prepare_list(limpeza),
    }
    return render(request, 'gira/lista_funcoes.html', context)

def assumir_funcao(request, pk):
    user = _get_user(request)
    if not user:
        return redirect('gira:login')

    funcao = get_object_or_404(Funcao, pk=pk)

    # regra: usuário comum não pode assumir cambones
    if 'cambone' in (funcao.tipo or '').lower() and not user.is_staff:
        messages.error(request, 'Você não pode assumir funções de cambone.')
        return redirect('gira:lista_funcoes')

    if funcao.status and funcao.status.lower() == 'preenchida':
        messages.warning(request, 'Esta função já está preenchida.')
        return redirect('gira:lista_funcoes')

    # atualiza
    funcao.pessoa = user
    funcao.status = 'Preenchida'
    funcao.save()

    Historico.objects.create(
        gira=funcao.gira,
        funcao=funcao,
        usuario=user,
        acao='Assumir',
        data=timezone.now(),
        info={'from_view': 'assumir_funcao'}
    )

    messages.success(request, 'Função assumida com sucesso.')
    return redirect('gira:lista_funcoes')

def logout_view(request):
    """Finaliza a sessão do usuário e redireciona para o login."""
    request.session.flush()
    return redirect('gira:login')
