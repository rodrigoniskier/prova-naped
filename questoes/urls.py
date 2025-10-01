# questoes/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # URLs existentes
    path('submeter/', views.submeter_questao, name='submeter_questao'),
    path('api/get-componentes/', views.get_componentes_por_periodo, name='api_get_componentes'),
    path('gerar-prova/', views.pagina_gerar_prova, name='pagina_gerar_prova'),
    path('prova-gerada/', views.prova_gerada_view, name='prova_gerada'),
    path('prova-gabarito/', views.prova_gabarito_view, name='prova_gabarito'),

    # --- ALTERAÇÃO PRINCIPAL DESTE PASSO ---
    # Adicionamos a nova API para buscar o histórico de questões.
    path('api/get-historico/', views.get_historico_questoes, name='api_get_historico'),
]