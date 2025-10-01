# gerador_provas/settings.py

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-chave-temporaria-para-emergencia')

DEBUG = True # Mantenha True no Codespaces, mudaremos para False antes do deploy final

ALLOWED_HOSTS = ['rodrigoniskier.pythonanywhere.com', 'localhost', '127.0.0.1', '.github.dev']


# Application definition
INSTALLED_APPS = [
    # --- ALTERAÇÃO PRINCIPAL DESTE PASSO ---
    # Adicionamos o 'jazzmin' ANTES do admin do Django. A ordem é importante.
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'questoes.apps.QuestoesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gerador_provas.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gerador_provas.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    { 'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator', },
    { 'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator', },
]

LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Recife'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = ['https://*.pythonanywhere.com', 'https://*.github.dev']


# --- ALTERAÇÃO PRINCIPAL DESTE PASSO ---
# Adicionamos as configurações de aparência do Jazzmin.
JAZZMIN_SETTINGS = {
    # Título da sua janela de login do admin (ex: "Entrar | Gerador de Provas")
    "site_title": "Gerador de Provas",

    # Texto no topo da página de login e do painel
    "site_header": "Gerador de Provas UNIPÊ",

    # Texto no canto superior esquerdo (substituído pelo logo se definido)
    "site_brand": "Medicina UNIPÊ",

    # Caminho para o logo (relativo à pasta 'static/')
    "site_logo": "images/naped.jpg",

    # Texto de boas-vindas na tela de login
    "welcome_sign": "Bem-vindo ao Gerador de Provas do curso de Medicina",
}