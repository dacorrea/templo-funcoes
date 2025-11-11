from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Gira, Funcao, Medium, Historico
from django.contrib.auth import get_user_model
from .models import User
from django.utils import timezone
import unicodedata
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Funcao, Medium, User  # ajuste import conforme seu arquivo


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



def _normalize(s: str) -> str:
    """Remove acentos e normaliza para comparação."""
    if not s:
        return ''
    s = s.lower()
    s = unicodedata.normalize('NFKD', s)
    return ''.join(ch for ch in s if not unicodedata.combining(ch))

def lista_funcoes(request):
    """Lista de funções da última gira, agrupadas por blocos (Cambones, Organização, Limpeza)."""
    user = _get_user(request)
    if not user:
        return redirect('gira:login')

    gira = Gira.objects.order_by('-data_hora').first()
    if not gira:
        messages.info(request, 'Nenhuma gira cadastrada.')
        return render(request, 'gira/lista_funcoes.html', {'user': user})

    # carrega funções; evita N+1
    funcoes_qs = gira.funcoes.select_related('medium_de_linha', 'pessoa').all().order_by('posicao')
    funcoes = list(funcoes_qs)

    cambones = []
    organizacao = []
    limpeza = []

    for f in funcoes:
        tipo = (f.tipo or '').lower()
        chave = (f.chave or '').lower()
        descricao = (f.descricao or '').lower()

        # heurística de agrupamento (tolerante)
        if 'cambone' in tipo or 'cambone' in chave or 'cambone' in descricao:
            cambones.append(f)
        elif any(k in tipo or k in chave or k in descricao for k in ['organ', 'senha', 'portão', 'portão', 'lojinh', 'chamar', 'organizar']):
            organizacao.append(f)
        elif 'limp' in tipo or 'limp' in chave or 'limp' in descricao:
            limpeza.append(f)
        else:
            organizacao.append(f)

    # --- Ordenação dos cambones: Mãe Bruna primeiro, depois alfabética pelo medium_de_linha.nome ---
    def _cambone_key(item):
        nome = item.medium_de_linha.nome if item.medium_de_linha else ''
        n = _normalize(nome)
        # garante que "mãe bruna" / "mae bruna" fique no topo
        if 'mae bruna' in n or 'mae' in n and 'bruna' in n or 'mãe bruna' in n:
            return ('', '')  # prioridade máxima
        return (n, nome or '')

    cambones.sort(key=_cambone_key)

    # --- Organização: forçamos ordem fixa para algumas funções comuns ---
    ordem_fix = ['portao', 'distribuir senha', 'lojinha', 'chamar senha']  # normalizados
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

    # --- Limpeza: padroniza display da descrição para "Limpeza" quando pertinente ---
    for f in limpeza:
        descr = (f.descricao or f.tipo or '')
        if 'limp' in (descr or '').lower():
            # adiciona atributo temporário para usar no template: f.display_descricao
            setattr(f, 'display_descricao', 'Limpeza')
        else:
            setattr(f, 'display_descricao', descr or f.tipo or 'Limpeza')

    # --- Tema ---
    linha = (gira.linha or '')
    nlinha = _normalize(linha)
    if 'exu' in nlinha or 'pombag' in nlinha:
        tema = 'exu'
    else:
        tema = 'padrao'

    contexto = {
    'user': user,                 # objeto do seu _get_user (mantém compatibilidade)
    'sess_user_id': user.id,      # id do gira_user (usado pelo template)
    'gira': gira,
    'cambones': cambones,
    'organizacao': organizacao_ordered,
    'limpeza': limpeza,
    'tema': tema,
}
return render(request, 'gira/lista_funcoes.html', contexto)





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





@require_POST
@csrf_exempt
def assumir_funcao(request):
    # usa o user_id guardado na sessão (login custom sem Django auth)
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

    # não permitir assumir cambone (regras do sistema)
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



