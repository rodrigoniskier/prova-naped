# questoes/views.py

from django.shortcuts import render, redirect
from django.forms import formset_factory
from django.http import JsonResponse
from .forms import QuestaoForm, AlternativaForm
from .models import Periodo, ComponenteCurricular, Alternativa, Questao
import random

def submeter_questao(request):
    # ... (esta função continua igual, sem alterações)
    AlternativaFormSet = formset_factory(AlternativaForm, extra=5, max_num=5)
    if request.method == 'POST':
        questao_form = QuestaoForm(request.POST, request.FILES)
        alternativa_formset = AlternativaFormSet(request.POST)
        if questao_form.is_valid() and alternativa_formset.is_valid():
            nova_questao = questao_form.save()
            for alternativa_form in alternativa_formset:
                if alternativa_form.cleaned_data:
                    texto = alternativa_form.cleaned_data.get('texto')
                    eh_correta = alternativa_form.cleaned_data.get('eh_correta', False)
                    if texto:
                        Alternativa.objects.create(
                            questao=nova_questao, texto=texto, eh_correta=eh_correta
                        )
            return redirect('submeter_questao')
    else:
        questao_form = QuestaoForm()
        alternativa_formset = AlternativaFormSet()
    periodos = Periodo.objects.all()
    context = {
        'questao_form': questao_form,
        'alternativa_formset': alternativa_formset,
        'periodos': periodos,
    }
    return render(request, 'questoes/submeter_questao.html', context)


def get_componentes_por_periodo(request):
    # ... (esta função continua igual, sem alterações)
    periodo_ids_str = request.GET.get('periodo_ids')
    periodo_id_str = request.GET.get('periodo_id')
    ids_para_filtrar = []
    if periodo_ids_str:
        ids_para_filtrar = periodo_ids_str.split(',')
    elif periodo_id_str:
        ids_para_filtrar = [periodo_id_str]
    if not ids_para_filtrar:
        return JsonResponse([], safe=False)
    componentes = ComponenteCurricular.objects.filter(periodo_id__in=ids_para_filtrar).order_by('nome')
    return JsonResponse(list(componentes.values('id', 'nome')), safe=False)


def get_historico_questoes(request):
    # ... (esta função continua igual, sem alterações)
    componente_id = request.GET.get('componente_id')
    if not componente_id:
        return JsonResponse([], safe=False)
    questoes = Questao.objects.filter(componente_id=componente_id).order_by('-id')
    return JsonResponse(list(questoes.values('id', 'enunciado', 'status')), safe=False)


def pagina_gerar_prova(request):
    # ... (esta função continua igual, sem alterações)
    periodos = Periodo.objects.all()
    context = {'periodos': periodos}
    return render(request, 'questoes/gerar_prova.html', context)


def prova_gerada_view(request):
    """
    Esta view agora gera a prova com as questões AGRUPADAS por componente.
    """
    componentes_ids = request.GET.getlist('componentes')
    if not componentes_ids:
        return redirect('pagina_gerar_prova')

    questoes_selecionadas = []
    # --- 1. ALTERAÇÃO PRINCIPAL ---
    # Buscamos os componentes já em ordem alfabética.
    componentes_da_prova = ComponenteCurricular.objects.filter(id__in=componentes_ids).order_by('nome')

    for componente in componentes_da_prova:
        questoes_aprovadas = list(Questao.objects.filter(componente=componente, status='APROVADA'))
        num_questoes = componente.numero_questoes_prova
        
        questoes_sorteadas = []
        if len(questoes_aprovadas) >= num_questoes:
            questoes_sorteadas = random.sample(questoes_aprovadas, num_questoes)
        else:
            questoes_sorteadas = questoes_aprovadas
        
        questoes_selecionadas.extend(questoes_sorteadas)

    # --- 2. ALTERAÇÃO PRINCIPAL ---
    # A linha que embaralhava tudo foi REMOVIDA.
    # random.shuffle(questoes_selecionadas)

    questao_ids = [q.id for q in questoes_selecionadas]

    context = {
        'componentes': componentes_da_prova,
        'questoes_selecionadas': questoes_selecionadas,
        'questao_ids': questao_ids,
    }
    return render(request, 'questoes/prova_template.html', context)


def prova_gabarito_view(request):
    # ... (esta função continua igual, sem alterações)
    ids_str = request.GET.get('ids')
    if not ids_str:
        return redirect('pagina_gerar_prova')
    ids_list = [int(id) for id in ids_str.split(',')]
    questoes = Questao.objects.filter(id__in=ids_list)
    questoes_mapeadas = {q.id: q for q in questoes}
    questoes_ordenadas = [questoes_mapeadas[id] for id in ids_list if id in questoes_mapeadas]
    componentes_ids = {q.componente.id for q in questoes_ordenadas}
    componentes = ComponenteCurricular.objects.filter(id__in=componentes_ids)
    context = {
        'componentes': componentes,
        'questoes_ordenadas': questoes_ordenadas,
    }
    return render(request, 'questoes/prova_gabarito.html', context)