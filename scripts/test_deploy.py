import importlib.util
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "deploy", Path(__file__).with_name("deploy_pythonanywhere.py")
)
deploy = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(deploy)


class BackupTests(unittest.TestCase):
    def test_backup_pode_ser_aberto_sem_alterar_banco_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = (
                Path(directory) / "original.sqlite3",
                Path(directory) / "backup.sqlite3",
            )
            with sqlite3.connect(source) as conn:
                conn.execute("CREATE TABLE django_migrations (id integer)")
                conn.execute("INSERT INTO django_migrations VALUES (1)")
            original_hash = deploy.checksum(source)
            digest = deploy.backup_sqlite(source, target)
            self.assertEqual(deploy.checksum(source), original_hash)
            self.assertEqual(digest, deploy.checksum(target))
            with sqlite3.connect(target) as conn:
                self.assertEqual(
                    conn.execute("SELECT id FROM django_migrations").fetchall(), [(1,)]
                )
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                deploy.backup_sqlite(source, target)

    def test_banco_ausente_nao_cria_banco_vazio(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "ausente", Path(directory) / "backup"
            with self.assertRaises(RuntimeError):
                deploy.backup_sqlite(source, target)
            self.assertFalse(source.exists())
            self.assertFalse(target.exists())

    def test_banco_que_nao_e_django_nao_e_aceito(self):
        with tempfile.TemporaryDirectory() as directory:
            source, target = Path(directory) / "original", Path(directory) / "backup"
            with sqlite3.connect(source) as conn:
                conn.execute("CREATE TABLE exemplo (id integer)")
            with self.assertRaises(RuntimeError):
                deploy.backup_sqlite(source, target)

    def test_conta_errada_nao_executa_comandos(self):
        with (
            patch.object(deploy.getpass, "getuser", return_value="outra-conta"),
            patch.object(deploy, "run") as run,
        ):
            with self.assertRaises(RuntimeError):
                deploy.main(
                    [
                        "--checkout",
                        ".",
                        "--approved-sha",
                        "a" * 40,
                        "--wsgi",
                        "wsgi.py",
                        "--backup-dir",
                        "/tmp/backup",
                    ]
                )
            run.assert_not_called()

    def test_sha_invalido_nao_executa_comandos(self):
        with (
            patch.object(deploy.getpass, "getuser", return_value="rodrigoniskier"),
            patch.object(deploy, "run") as run,
        ):
            with self.assertRaises(RuntimeError):
                deploy.main(
                    [
                        "--checkout",
                        ".",
                        "--approved-sha",
                        "main",
                        "--wsgi",
                        "wsgi.py",
                        "--backup-dir",
                        "/tmp/backup",
                    ]
                )
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
