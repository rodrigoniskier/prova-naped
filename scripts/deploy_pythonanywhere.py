#!/usr/bin/env python3
"""Executar no virtualenv confirmado da aplicação; nunca executa restauração de dados."""

import argparse
import fcntl
import getpass
import hashlib
import importlib.metadata
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

DOMAIN = "rodrigoniskier.pythonanywhere.com"
OWNER = "rodrigoniskier"
ORIGINS = {
    "https://github.com/rodrigoniskier/prova-naped.git",
    "https://github.com/rodrigoniskier/prova-naped",
    "git@github.com:rodrigoniskier/prova-naped.git",
}


def run(*args, capture=False):
    return subprocess.run(
        args, check=True, text=True, stdout=subprocess.PIPE if capture else None
    ).stdout


def checksum(path):
    with path.open("rb") as arquivo:
        return hashlib.file_digest(arquivo, "sha256").hexdigest()


def backup_sqlite(source, destination):
    if not source.is_file():
        raise RuntimeError("Banco SQLite não encontrado; nenhum banco vazio será criado.")
    descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(descriptor)
    with sqlite3.connect(f"file:{quote(str(source.resolve()))}?mode=ro", uri=True) as origem:
        if origem.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise RuntimeError("Banco de origem reprovado no integrity_check.")
        with sqlite3.connect(destination) as backup:
            origem.backup(backup)
    # Abrir a cópia, consultar esquema e validar integridade prova recuperabilidade
    # estrutural sem restaurar por cima de transações legítimas da produção.
    with sqlite3.connect(f"file:{quote(str(destination))}?mode=ro", uri=True) as backup:
        if backup.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise RuntimeError("Backup reprovado no integrity_check.")
        if backup.execute("PRAGMA foreign_key_check").fetchall():
            raise RuntimeError("Backup contém referências inválidas.")
        if not backup.execute(
            "SELECT 1 FROM sqlite_master WHERE name='django_migrations'"
        ).fetchone():
            raise RuntimeError("Backup não contém o banco Django esperado.")
    return checksum(destination)


def api(method, suffix, token):
    url = f"https://www.pythonanywhere.com/api/v0/user/{OWNER}/webapps/{DOMAIN}/{suffix}"
    pedido = Request(
        url,
        method=method,
        data=b"" if method == "POST" else None,
        headers={"Authorization": f"Token {token}"},
    )
    # POST de reload nunca é repetido automaticamente se a resposta for ambígua.
    with urlopen(pedido, timeout=60) as resposta:
        if resposta.status != 200:
            raise RuntimeError(f"API retornou HTTP {resposta.status}.")
        return json.load(resposta)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, required=True)
    parser.add_argument("--approved-sha", required=True)
    parser.add_argument("--wsgi", type=Path, required=True)
    parser.add_argument("--backup-dir", type=Path, required=True)
    parser.add_argument(
        "--reload-via-ui",
        action="store_true",
        help="Preparar código e banco; reload pela UI deve ser comprovado separadamente.",
    )
    args = parser.parse_args(argv)
    if getpass.getuser() != OWNER or not re.fullmatch("[0-9a-f]{40}", args.approved_sha):
        raise RuntimeError("Conta ou SHA aprovado inválido.")
    checkout = args.checkout.resolve(strict=True)
    backup_dir = args.backup_dir.resolve()
    if backup_dir == checkout or checkout in backup_dir.parents:
        raise RuntimeError("Backups devem ficar fora do repositório.")
    os.chdir(checkout)
    if run("git", "remote", "get-url", "origin", capture=True).strip() not in ORIGINS:
        raise RuntimeError("Origin não corresponde ao repositório autorizado.")
    if run("git", "branch", "--show-current", capture=True).strip() != "main":
        raise RuntimeError("A branch de produção deve ser main.")
    if run("git", "status", "--porcelain", capture=True).strip():
        raise RuntimeError(
            "Checkout com modificações locais: preserve e investigue antes de continuar."
        )
    wsgi = args.wsgi.read_text()
    if str(checkout) not in wsgi or "gerador_provas.settings" not in wsgi:
        raise RuntimeError("WSGI não confirma este checkout e módulo de configurações.")
    token = os.environ.get("API_TOKEN") or os.environ.get("PYTHONANYWHERE_API_TOKEN")
    if not args.reload_via_ui:
        if not token:
            raise RuntimeError(
                "API sem autenticação. Use a UI autenticada, sem copiar tokens para logs."
            )
        config = api("GET", "", token)
        if Path(config.get("source_directory") or "/invalid").resolve() != checkout:
            raise RuntimeError("Source directory da API diverge do checkout.")
        if (
            Path(config.get("virtualenv_path") or "/invalid").resolve()
            != Path(sys.prefix).resolve()
        ):
            raise RuntimeError(
                "O Python atual não pertence ao virtualenv configurado na aplicação."
            )
    elif sys.prefix == sys.base_prefix:
        raise RuntimeError("Execute com o Python do virtualenv confirmado no painel.")
    sys.path.insert(0, str(checkout))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gerador_provas.settings")
    import django

    django.setup()
    from django.conf import settings

    database = settings.DATABASES["default"]
    if database["ENGINE"] != "django.db.backends.sqlite3":
        raise RuntimeError("Este script exige SQLite. Prepare backup nativo para outro banco.")
    previous_sha = run("git", "rev-parse", "HEAD", capture=True).strip()
    run(sys.executable, "manage.py", "check")
    run(sys.executable, "manage.py", "showmigrations", "--plan")
    run("git", "fetch", "origin", "main")
    if run("git", "rev-parse", "origin/main", capture=True).strip() != args.approved_sha:
        raise RuntimeError("main divergiu do commit aprovado. Revalidar antes do deploy.")
    run("git", "merge-base", "--is-ancestor", previous_sha, args.approved_sha)
    backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    snapshot = backup_dir / f"{stamp}-{previous_sha[:12]}.sqlite3"
    digest = backup_sqlite(Path(database["NAME"]), snapshot)
    manifest = {
        "status": "BACKUP_VALIDADO",
        "domain": DOMAIN,
        "previous_sha": previous_sha,
        "approved_sha": args.approved_sha,
        "backup": str(snapshot),
        "backup_sha256": digest,
        "checkout": str(checkout),
        "python": sys.executable,
        "wsgi": str(args.wsgi),
        "packages_before": {
            d.metadata["Name"]: d.version for d in importlib.metadata.distributions()
        },
    }
    record = snapshot.with_suffix(".json")
    record.write_text(json.dumps(manifest, indent=2))
    record.chmod(0o600)
    print(f"BACKUP_VALIDADO {snapshot} sha256={digest}; anterior={previous_sha}", flush=True)
    # SHA imutável evita puxar outro commit se main avançar durante o pull.
    run("git", "pull", "--ff-only", "origin", args.approved_sha)
    if run("git", "rev-parse", "HEAD", capture=True).strip() != args.approved_sha:
        raise RuntimeError("HEAD não corresponde ao commit aprovado.")
    changed = run(
        "git", "diff", "--name-only", previous_sha, args.approved_sha, capture=True
    ).splitlines()
    if "requirements.txt" in changed:
        run(sys.executable, "-m", "pip", "install", "-r", "requirements.txt")
    run(sys.executable, "-m", "pip", "check")
    run(sys.executable, "manage.py", "check")
    run(sys.executable, "manage.py", "check", "--deploy")
    run(sys.executable, "manage.py", "migrate", "--plan")
    run(sys.executable, "manage.py", "migrate", "--noinput")
    run(sys.executable, "manage.py", "migrate", "--check")
    if settings.STATIC_ROOT:
        run(sys.executable, "manage.py", "collectstatic", "--noinput")
    manifest["status"] = "CODIGO_E_BANCO_ATUALIZADOS_RELOAD_PENDENTE"
    record.write_text(json.dumps(manifest, indent=2))
    if not args.reload_via_ui:
        api("POST", "reload/", token)
        manifest["status"] = "RELOAD_ACEITO_SMOKE_AUTENTICADO_PENDENTE"
        record.write_text(json.dumps(manifest, indent=2))
    print(manifest["status"], flush=True)
    print("Verifique logs e fluxo autenticado. Não crie questões reais como teste.", flush=True)


if __name__ == "__main__":
    # Um lock por aplicação impede dois deploys simultâneos no mesmo servidor.
    lock_dir = Path.home() / ".cache"
    lock_dir.mkdir(exist_ok=True)
    with (lock_dir / "prova-naped-deploy.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        main()
