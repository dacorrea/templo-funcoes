from django.shortcuts import render, redirect, get_object_or_404
from .models import User, UserProfile, Funcao, Gira, Medium, CambonePool, Historico
from .forms import LoginPhoneForm, GiraForm, FuncaoEditForm
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth import logout


def login_view(request):
    if request.method == 'POST':
        form = LoginPhoneForm(request.POST)
        if form.is_valid():
            celular = ''.join(ch for ch in form.cleaned_data['celular'] if ch.isdigit())
            try:
                # Tenta encontrar o usuário pelo telefone
                user = User.objects.get(telefone__endswith=celular, ativo=True)
                # Busca o UserProfile correspondente
                profile = UserProfile.objects.filter(user=user, ativo=True).first()
                if not profile:
                    messages.error(request, 'Usuário não possui perfil ativo.')
                    return render(request, 'gira/login.html', {'form': form})

                # Login simples via sessão
                request.session['userprofile_id'] = profile.id
                return redirect('gira:lista_funcoes')

            except User.DoesNotExist:
                messages.error(request, 'Usuário não tem permissão de acesso.')
    else:
        form = LoginPhoneForm()
    return render(request, 'gira/login.html', {'form': form})


def _get_user(request):
    uid = request.session.get('userprofile_id')
    if not uid:
        return None
    try:
        return UserProfile.objects.get(id=uid)
    except UserProfile.DoesNotExist:
        return None


def lista_funcoes(request):
    user = _get_user(request)
    if not user:
        return redirect('gira:login')

    gira = Gira.objects.order_by('-data_hora').first()
    if not gira:
        messages.info(request, 'Nenhuma gira criada.')
        return render(request, 'gira/lista_funcoes.html', {'user': user})

    funcoes = gira.funcoes.all().order_by('tipo', 'posicao')
    cambones = funcoes.filter(tipo='Cambones')
    organizacao = funcoes.filter(tipo='Organizacao')
    limpeza = funcoes.filter(tipo='Limpeza')

    return render(request, 'gira/lista_funcoes.html', {
        'user': user, 'gira': gira,
        'cambones': cambones, 'organizacao': organizacao, 'limpeza': limpeza
    })


def funcao_detail(request, pk):
    user = _get_user(request)
    if not user:
        return redirect('gira:login')
    f = get_object_or_404(Funcao, pk=pk)
    users = UserProfile.objects.filter(ativo=True)
    if request.method == 'POST':
        if user.role == 'admin':
            form = FuncaoEditForm(request.POST, instance=f)
            if form.is_valid():
                form.save()
                Historico.objects.create(
                    gira=f.gira, funcao=f, usuario=user, acao='edit',
                    info={'pessoa': str(f.pessoa.id) if f.pessoa else None}
                )
                messages.success(request, 'Salvo.')
                return redirect('gira:funcao_detail', pk=pk)
    return render(request, 'gira/funcao_detail.html', {'f': f, 'user': user, 'users': users})


def assumir_funcao(request, pk):
    user = _get_user(request)
    if not user:
        return redirect('gira:login')
    f = get_object_or_404(Funcao, pk=pk)
    if f.status == 'Vaga':
        if f.tipo == 'Cambones' and user.role != 'admin':
            messages.error(request, 'Apenas administradores podem assumir cambones.')
            return redirect('gira:lista_funcoes')
        f.pessoa = user
        f.status = 'Preenchida'
        f.save()
        Historico.objects.create(gira=f.gira, funcao=f, usuario=user, acao='assumir', info={'pessoa': user.nome})
        messages.success(request, 'Função assumida.')
    else:
        messages.warning(request, 'Vaga já preenchida.')
    return redirect('gira:lista_funcoes')


def liberar_funcao(request, pk):
    user = _get_user(request)
    if not user or user.role != 'admin':
        messages.error(request, 'Somente administradores podem liberar vagas.')
        return redirect('gira:lista_funcoes')
    f = get_object_or_404(Funcao, pk=pk)
    f.pessoa = None
    f.status = 'Vaga'
    f.save()
    Historico.objects.create(gira=f.gira, funcao=f, usuario=user, acao='liberar')
    messages.success(request, 'Vaga liberada.')
    return redirect('gira:lista_funcoes')


def criar_gira(request):
    user = _get_user(request)
    if not user or user.role != 'admin':
        messages.error(request, 'Apenas admin.')
        return redirect('gira:lista_funcoes')
    if request.method == 'POST':
        form = GiraForm(request.POST)
        if form.is_valid():
            gira = form.save(commit=False)
            gira.criado_por = user
            gira.save()
            lines = request.POST.get('functions_csv', '').splitlines()
            for i, l in enumerate(lines):
                parts = [p.strip() for p in l.split(';')]
                if len(parts) >= 2:
                    tipo, pos = parts[0], parts[1]
                    Funcao.objects.create(gira=gira, chave=f"{gira.id}-{i}", tipo=tipo, posicao=pos, descricao=parts[2] if len(parts) > 2 else '')
            messages.success(request, 'Gira criada.')
            return redirect('gira:lista_funcoes')
    else:
        form = GiraForm()
    mediums = Medium.objects.filter(habilitado=True)
    cambones = CambonePool.objects.filter(ativo=True).order_by('ordem')
    return render(request, 'gira/criar_gira.html', {'form': form, 'mediums': mediums, 'cambones': cambones})


def logout_view(request):
    request.session.pop('userprofile_id', None)
    return redirect('gira:login')
