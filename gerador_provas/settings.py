# gerador_provas/settings.py

from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-chave-temporaria-para-emergencia')

# Lembre-se de mudar para False antes do deploy final, se estiver testando no Codespaces.
DEBUG = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = ['rodrigoniskier.pythonanywhere.com', 'localhost', '127.0.0.1', '.github.dev']


# Application definition
INSTALLED_APPS = [
    'jazzmin',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'questoes.apps.QuestoesConfig',
]

# ... (Middleware, Root_URLConf, Templates, WSGI, Databases, Auth_Password_Validators - sem alterações) ...
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


# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Recife'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# --- ALTERAÇÃO PRINCIPAL DESTE PASSO ---
# Adicionamos esta linha para dizer ao Django onde encontrar a pasta 'static' da nossa app.
STATICFILES_DIRS = [
    BASE_DIR / 'questoes/static',
]


# Media files (User uploads)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ... (Jazzmin Settings e UI Tweaks - sem alterações) ...
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_TRUSTED_ORIGINS = ['https://*.pythonanywhere.com', 'https://*.github.dev']
JAZZMIN_SETTINGS = {
    "site_title": "Gerador de Provas",
    "site_header": "Gerador Provas",
    "site_brand": "Medicina UNIPÊ",
    "site_logo": "images/naped.jpg",
    "login_logo": "images/logo.jpg",
    "login_logo_max_size": "250px",
    "welcome_sign": "Bem-vindo ao Gerador de Provas do curso de Medicina",
    "copyright": "Medicina UNIPÊ",
    "custom_css": "css/admin_custom.css",
}
JAZZMIN_UI_TWEAKS = {
    "theme": "darkly",
    "body_classes": "gradient-bg",
}