from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
import unicodedata




# -------------------------------------------------------------------
# 🔹 Funções utilitárias
# -------------------------------------------------------------------

def check_user_model(request):
    User = get_user_model()
    return JsonResponse({
        "auth_user_model": str(User),
        "db_table": User._meta.db_table,
        "fields": [f.name for f in User._meta.fields],
    })


def _get_user(request):
    """Retorna o usuário logado via sessão (login custom)."""
    uid = request.session.get('user_id')
    if not uid:
        return None
    try:
        return User.objects.get(id=uid)
    except User.DoesNotExist:
        return None


def _normalize(s: str) -> str:
    """Remove acentos e normaliza texto para comparação."""
    if not s:
        return ''
    s = s.lower()
    s = unicodedata.normalize('NFKD', s)
    return ''.join(ch for ch in s if not unicodedata.combining(ch))


# -------------------------------------------------------------------
# 🔹 Login e Logout
# -------------------------------------------------------------------

def login_view(request):
    user = _get_user(request)
    if user:
        return redirect('gira:lista_funcoes')
        
    if request.method == 'POST':
        celular = ''.join(ch for ch in request.POST.get('celular', '') if ch.isdigit())
        try:
            user = User.objects.get(celular=celular, is_active=True)
        except User.DoesNotExist:
            messages.error(request, 'Celular não encontrado ou usuário inativo.')
            return render(request, 'gira/login.html')

        # guarda dados mínimos na sessão
        request.session['user_id'] = user.id
        request.session['user_nome'] = user.nome
        request.session['user_telefone'] = user.celular

        return redirect('gira:lista_funcoes')

    return render(request, 'gira/login.html')


def logout_view(request):
    """Finaliza a sessão do usuário e redireciona para o login."""
    request.session.flush()
    return redirect('gira:login')


# -------------------------------------------------------------------
# 🔹 View principal: lista de funções
# -------------------------------------------------------------------
def lista_funcoes(request):
    user = _get_user(request)
    if not user:
        return redirect('gira:login')

    # 🔍 Vincula o usuário logado ao médium correspondente
    medium_logado = Medium.objects.filter(user_id=user.id).first()

    # LOG de diagnóstico para monitoramento
    print(f"[DEBUG] Usuário logado: {user.nome} (gira_user.id={user.id})")
    if medium_logado:
        print(f"[DEBUG] Médium logado: {medium_logado.nome} (gira_medium.id={medium_logado.id})")
    else:
        print("[DEBUG] Nenhum médium associado a este usuário!")

    gira = Gira.objects.order_by('-data_hora').first()
    if not gira:
        messages.info(request, 'Nenhuma gira cadastrada.')
        return render(request, 'gira/lista_funcoes.html', {'user': user})

    funcoes = list(
        gira.funcoes.select_related('medium_de_linha', 'pessoa').all().order_by('posicao')
    )

    cambones, organizacao, limpeza = [], [], []

    # Agrupamento das funções
    for f in funcoes:
        tipo = (f.tipo or '').lower()
        chave = (f.chave or '').lower()
        descricao = (f.descricao or '').lower()

        if 'cambone' in tipo or 'cambone' in chave or 'cambone' in descricao:
            cambones.append(f)
        elif any(k in tipo or k in chave or k in descricao for k in ['organ', 'senha', 'portão', 'portão', 'lojinh', 'chamar']):
            organizacao.append(f)
        elif 'limp' in tipo or 'limp' in chave or 'limp' in descricao:
            limpeza.append(f)
        else:
            organizacao.append(f)

    # Ordenação de Cambones (“Mãe Bruna” primeiro)
    def _cambone_key(item):
        nome = item.medium_de_linha.nome if item.medium_de_linha else ''
        n = _normalize(nome)
        if 'mae bruna' in n or ('mae' in n and 'bruna' in n):
            return ('', '')
        return (n, nome or '')

    cambones.sort(key=_cambone_key)

    # Organização – ordem fixa
    ordem_fix = ['portao', 'distribuir senha', 'lojinha', 'chamar senha']
    buckets = {k: [] for k in ordem_fix}
    others = []
    for f in organizacao:
        descr = _normalize(f.descricao or f.tipo or '')
        placed = False
        for key in ordem_fix:
            if key in descr:
                buckets[key].append(f)
                placed = True
                break
        if not placed:
            others.append(f)

    organizacao_ordered = []
    for key in ordem_fix:
        organizacao_ordered.extend(buckets[key])
    organizacao_ordered.extend(others)

    # Limpeza – padroniza descrição
    for f in limpeza:
        descr = (f.descricao or f.tipo or '')
        setattr(f, 'display_descricao', 'Limpeza' if 'limp' in descr.lower() else descr or f.tipo or 'Limpeza')

    # Tema dinâmico
    linha = _normalize(gira.linha or '')
    tema = 'exu' if 'exu' in linha or 'pombag' in linha else 'padrao'

    # Debug: quais funções têm pessoa_id igual ao médium logado
    if medium_logado:
        meus_ids = [f.id for f in funcoes if f.pessoa_id == medium_logado.id]
        print(f"[DEBUG] Funções assumidas por {medium_logado.nome}: {meus_ids}")

    contexto = {
        'user': user,
        'sess_user_id': user.id,  # gira_user.id (mantém compatibilidade)
        'medium_logado': medium_logado,  # gira_medium associado
        'gira': gira,
        'cambones': cambones,
        'organizacao': organizacao_ordered,
        'limpeza': limpeza,
        'tema': tema,
    }
    return render(request, 'gira/lista_funcoes.html', contexto)


# -------------------------------------------------------------------
# 🔹 Endpoints AJAX: assumir / desistir função
# -------------------------------------------------------------------

@require_POST
@csrf_exempt
def assumir_funcao(request):
    sess_user_id = request.session.get('user_id')
    if not sess_user_id:
        return JsonResponse({'status': 'erro', 'mensagem': 'Usuário não autenticado.'}, status=401)

    funcao_id = request.POST.get('funcao_id')
    if not funcao_id:
        return JsonResponse({'status': 'erro', 'mensagem': 'ID da função ausente.'}, status=400)

    try:
        medium = Medium.objects.get(user_id=sess_user_id)
    except Medium.DoesNotExist:
        return JsonResponse({'status': 'erro', 'mensagem': 'Médium não encontrado para o usuário.'}, status=404)

    try:
        funcao = Funcao.objects.get(id=funcao_id)
    except Funcao.DoesNotExist:
        return JsonResponse({'status': 'erro', 'mensagem': 'Função inexistente.'}, status=404)

    if funcao.pessoa_id:
        return JsonResponse({'status': 'erro', 'mensagem': 'Esta função já foi assumida.'}, status=409)

    if (funcao.tipo or '').lower().startswith('cambone'):
        return JsonResponse({'status': 'erro', 'mensagem': 'Não é permitido assumir cambones via UI.'}, status=403)

    funcao.pessoa_id = medium.id
    funcao.status = 'Preenchida'
    funcao.save()

    return JsonResponse({'status': 'ok', 'mensagem': f'Função assumida por {medium.nome}', 'funcao_id': funcao.id})


@require_POST
@csrf_exempt
def desistir_funcao(request):
    sess_user_id = request.session.get('user_id')
    if not sess_user_id:
        return JsonResponse({'status': 'erro', 'mensagem': 'Usuário não autenticado.'}, status=401)

    funcao_id = request.POST.get('funcao_id')
    if not funcao_id:
        return JsonResponse({'status': 'erro', 'mensagem': 'ID da função ausente.'}, status=400)

    try:
        medium = Medium.objects.get(user_id=sess_user_id)
    except Medium.DoesNotExist:
        return JsonResponse({'status': 'erro', 'mensagem': 'Médium não encontrado para o usuário.'}, status=404)

    try:
        funcao = Funcao.objects.get(id=funcao_id)
    except Funcao.DoesNotExist:
        return JsonResponse({'status': 'erro', 'mensagem': 'Função inexistente.'}, status=404)

    if funcao.pessoa_id != medium.id:
        return JsonResponse({'status': 'erro', 'mensagem': 'Você não é responsável por esta função.'}, status=403)

    funcao.pessoa_id = None
    funcao.status = 'Vaga'
    funcao.save()

    return JsonResponse({'status': 'ok', 'mensagem': f'{medium.nome} desistiu da função.', 'funcao_id': funcao.id})


# -------------------------------------------------------------------
# 🔹 View da lista funções em desenvolvimento
# -------------------------------------------------------------------
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from .models import Gira, Funcao, Medium, Historico, User, GiraFuncaoHistorico

def lista_funcoes_dev(request, gira_id=None):
    """
    Página de desenvolvimento /funcoes_dev/
    - Idêntica à lista_funcoes, mas usa gira_funcao_historico.
    - Acesso restrito a superusers.
    """

    user = _get_user(request)
    if not user:
        return redirect('gira:login')

    if not getattr(user, "is_superuser", False):
        return render(request, "gira/acesso_negado.html", {"mensagem": "Acesso restrito."})

    # 🔍 Obtém médium vinculado
    try:
        medium_logado = Medium.objects.filter(user_id=user.id).first()
    except Medium.DoesNotExist:
        medium_logado = None

    gira = Gira.objects.order_by('-data_hora').first() if not gira_id else Gira.objects.filter(id=gira_id).first()
    if not gira:
        messages.info(request, 'Nenhuma gira cadastrada.')
        return render(request, 'gira/lista_funcoes.html', {'user': user})

    # 🔹 Busca as funções do histórico
    funcoes = list(
        GiraFuncaoHistorico.objects.filter(gira_id=gira.id)
        .select_related('medium_de_linha', 'pessoa')
        .order_by('posicao')
    )

    cambones, organizacao, limpeza = [], [], []
    for f in funcoes:
        tipo = (f.tipo or '').lower()
        chave = (f.chave or '').lower()
        descricao = (f.descricao or '').lower()

        if 'cambone' in tipo or 'cambone' in chave or 'cambone' in descricao:
            cambones.append(f)
        elif any(k in tipo or k in chave or k in descricao for k in ['organ', 'senha', 'portão', 'portão', 'lojinh', 'chamar']):
            organizacao.append(f)
        elif 'limp' in tipo or 'limp' in chave or 'limp' in descricao:
            limpeza.append(f)
        else:
            organizacao.append(f)

    def _cambone_key(item):
        nome = item.medium_de_linha.nome if item.medium_de_linha else ''
        n = _normalize(nome)
        if 'mae bruna' in n or ('mae' in n and 'bruna' in n):
            return ('', '')
        return (n, nome or '')
    cambones.sort(key=_cambone_key)

    ordem_fix = ['portao', 'distribuir senha', 'lojinha', 'chamar senha']
    buckets = {k: [] for k in ordem_fix}
    others = []
    for f in organizacao:
        descr = _normalize(f.descricao or f.tipo or '')
        placed = False
        for key in ordem_fix:
            if key in descr:
                buckets[key].append(f)
                placed = True
                break
        if not placed:
            others.append(f)

    organizacao_ordered = []
    for key in ordem_fix:
        organizacao_ordered.extend(buckets[key])
    organizacao_ordered.extend(others)

    for f in limpeza:
        descr = (f.descricao or f.tipo or '')
        setattr(f, 'display_descricao', 'Limpeza' if 'limp' in descr.lower() else descr or f.tipo or 'Limpeza')

    linha = _normalize(gira.linha or '')
    tema = 'exu' if 'exu' in linha or 'pombag' in linha else 'padrao'

    # 🧭 Carrossel: gira anterior e próxima
    gira_anterior = Gira.objects.filter(data_hora__lt=gira.data_hora).order_by('-data_hora').first()
    gira_proxima = Gira.objects.filter(data_hora__gt=gira.data_hora).order_by('data_hora').first()

    contexto = {
        'user': user,
        'sess_user_id': user.id,
        'medium_logado': medium_logado,
        'gira': gira,
        'cambones': cambones,
        'organizacao': organizacao_ordered,
        'limpeza': limpeza,
        'tema': tema,
        'gira_anterior': gira_anterior,
        'gira_proxima': gira_proxima,
    }
    return render(request, 'gira/lista_funcoes_dev.html', contexto)
