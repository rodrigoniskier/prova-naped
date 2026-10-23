"""Configuração de testes: nunca usa o banco nem a mídia do checkout."""

import os
import tempfile
from pathlib import Path

from .settings import *  # noqa: F403

SECRET_KEY = "chave-exclusiva-dos-testes-sem-dados-reais"
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {
            "NAME": str(Path(tempfile.gettempdir()) / f"prova-naped-tests-{os.getpid()}.sqlite3")
        },
        "OPTIONS": {"timeout": 20},
    }
}
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
