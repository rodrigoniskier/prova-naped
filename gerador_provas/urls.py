# gerador_provas/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # A URL do admin agora é a primeira e única no nível raiz.
    path('admin/', admin.site.urls),
    
    # TODAS as nossas URLs da aplicação 'questoes' agora começarão com 'app/'.
    # Isso evita o conflito e o loop de recursão.
    path('app/', include('questoes.urls')),
]

# Configuração para servir arquivos de mídia durante o desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)