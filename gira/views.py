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
    """Lista de funções da última gira, agrupadas por blocos (Cambones, Organização, Limpeza)."""
    user = _get_user(request)
    if not user:
        return redirect('gira:login')

    gira = Gira.objects.order_by('-data_hora').first()
    if not gira:
        messages.info(request, 'Nenhuma gira cadastrada.')
        return render(request, 'gira/lista_funcoes.html', {'user': user})

    # Carrega todas as funções com joins para evitar N+1
    funcoes = list(gira.funcoes.select_related('medium_de_linha', 'pessoa').all().order_by('posicao'))

    # Agrupa por bloco com heurística tolerante (aceita variações no campo tipo)
    cambones = []
    organizacao = []
    limpeza = []

    for f in funcoes:
        tipo = (f.tipo or '').lower()
        chave = (f.chave or '').lower()
        descricao = (f.descricao or '').lower()

        # Detecta cambone por tipo ou por chave/descrição
        if 'cambone' in tipo or 'cambone' in chave or 'cambone' in descricao:
            cambones.append(f)
        # Organização: palavras-chave típicas
        elif any(k in tipo or k in chave or k in descricao for k in ['organ', 'senha', 'portão', 'lojinha', 'chamar', 'organizar']):
            organizacao.append(f)
        # Limpeza: por 'limp'
        elif 'limp' in tipo or 'limp' in chave or 'limp' in descricao:
            limpeza.append(f)
        else:
            # fallback: coloca em organização para não sumir
            organizacao.append(f)

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
