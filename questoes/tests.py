import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, close_old_connections
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from .importacao import importar_questoes
from .models import (
    Alternativa,
    ComponenteCurricular,
    ImportacaoQuestao,
    Periodo,
    Questao,
    SemestreLetivo,
)


class DadosImportacao:
    def setUp(self):
        super().setUp()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.media = override_settings(MEDIA_ROOT=self.tmp.name)
        self.media.enable()
        self.addCleanup(self.media.disable)
        self.usuario = get_user_model().objects.create_superuser(
            "admin", "admin@example.test", "teste"
        )
        self.periodo = Periodo.objects.create(nome="1º Período")
        self.doador = ComponenteCurricular.objects.create(nome="Doador", periodo=self.periodo)
        self.receptor = ComponenteCurricular.objects.create(nome="Receptor", periodo=self.periodo)
        self.outro = ComponenteCurricular.objects.create(
            nome="Fora do semestre", periodo=self.periodo
        )
        self.semestre = SemestreLetivo.objects.create(nome="2026.2", ativo=True)
        self.semestre.componentes.add(self.doador, self.receptor)
        self.questao = self.nova_questao()
        self.url = reverse("admin:questoes_importar")
        self.client.force_login(self.usuario)

    def nova_questao(self, **kwargs):
        questao = Questao.objects.create(
            componente=kwargs.pop("componente", self.doador),
            enunciado=kwargs.pop("enunciado", "Qual alternativa?"),
            texto_base="<p>Texto formatado</p>",
            justificativa="Justificativa pedagógica",
            status="APROVADA",
            **kwargs,
        )
        Alternativa.objects.bulk_create(
            [
                Alternativa(questao=questao, texto="Primeira", eh_correta=False),
                Alternativa(questao=questao, texto="Segunda", eh_correta=True),
            ]
        )
        return questao

    def importar(self, ids=None, **kwargs):
        dados = dict(
            usuario=self.usuario,
            semestre_id=self.semestre.pk,
            doador_id=self.doador.pk,
            receptor_id=self.receptor.pk,
            questao_ids=ids if ids is not None else [self.questao.pk],
        )
        dados.update(kwargs)
        return importar_questoes(**dados)

    def contexto(self, **kwargs):
        return dict(semestre=self.semestre.pk, doador=self.doador.pk, **kwargs)

    def pagina(self):
        return self.client.get(self.url, self.contexto())

    def postar(self, anterior, acao="confirmar", marcadas=None, **kwargs):
        dados = self.contexto(receptor=self.receptor.pk)
        dados.update(
            estado=anterior.context["estado"],
            acao=acao,
            marcadas=marcadas if marcadas is not None else [self.questao.pk],
        )
        dados.update(kwargs)
        return self.client.post(self.url, dados)


class ServicoImportacaoTests(DadosImportacao, TestCase):
    def test_questao_alternativas_gabarito_pendente_e_auditoria(self):
        resultado = self.importar()
        self.assertEqual((resultado.importadas, resultado.ignoradas), (1, 0))
        copia = Questao.objects.get(componente=self.receptor)
        self.assertNotEqual(copia.pk, self.questao.pk)
        for campo in ("texto_base", "enunciado", "justificativa"):
            self.assertEqual(getattr(copia, campo), getattr(self.questao, campo))
        self.assertEqual(copia.status, "PENDENTE")
        self.assertEqual(
            list(copia.alternativas.order_by("pk").values_list("texto", "eh_correta")),
            [("Primeira", False), ("Segunda", True)],
        )
        self.assertFalse(
            set(copia.alternativas.values_list("pk", flat=True))
            & set(self.questao.alternativas.values_list("pk", flat=True))
        )
        registro = ImportacaoQuestao.objects.get(copia=copia)
        self.assertEqual(registro.origem, self.questao)
        self.assertEqual(registro.responsavel, self.usuario)
        self.assertEqual(registro.semestre, self.semestre)
        self.assertIsNotNone(registro.criada_em)
        self.questao.refresh_from_db()
        self.assertEqual(self.questao.status, "APROVADA")

    def test_multiplas_e_enunciados_iguais_nao_sao_duplicatas(self):
        outra = self.nova_questao()
        self.assertEqual(self.importar([self.questao.pk, outra.pk]).importadas, 2)

    def test_reenvio_ignora_e_nao_recria_copia_excluida(self):
        self.importar()
        self.assertEqual(self.importar().ignoradas, 1)
        Questao.objects.filter(componente=self.receptor).delete()
        self.assertEqual(self.importar().ignoradas, 1)
        self.assertIsNone(ImportacaoQuestao.objects.get().copia)

    def test_edicao_e_exclusao_independentes(self):
        self.importar()
        copia = Questao.objects.get(componente=self.receptor)
        copia.enunciado = "Editada"
        copia.save()
        copia.alternativas.update(texto="Editada")
        self.questao.refresh_from_db()
        self.assertEqual(self.questao.enunciado, "Qual alternativa?")
        self.assertEqual(self.questao.alternativas.order_by("pk").first().texto, "Primeira")
        self.questao.delete()
        copia.refresh_from_db()
        self.assertEqual(copia.alternativas.count(), 2)
        self.assertIsNone(ImportacaoQuestao.objects.get().origem)
        copia.delete()
        self.assertEqual(ImportacaoQuestao.objects.count(), 1)

    def test_imagem_tem_arquivo_independente_e_sobrevive_exclusao_origem(self):
        self.questao.imagem.save("original.png", ContentFile(b"imagem de teste"), save=True)
        self.importar()
        copia = Questao.objects.get(componente=self.receptor)
        self.assertNotEqual(copia.imagem.name, self.questao.imagem.name)
        self.assertEqual(copia.imagem.read(), b"imagem de teste")
        self.questao.imagem.delete()
        self.questao.delete()
        self.assertTrue(copia.imagem.storage.exists(copia.imagem.name))

    def test_excluir_arquivo_copia_preserva_original(self):
        self.questao.imagem.save("original.png", ContentFile(b"original"), save=True)
        self.importar()
        copia = Questao.objects.get(componente=self.receptor)
        copia.imagem.delete()
        copia.delete()
        self.assertTrue(self.questao.imagem.storage.exists(self.questao.imagem.name))

    def test_inativo(self):
        self.semestre.ativo = False
        self.semestre.save()
        with self.assertRaises(ValidationError):
            self.importar()

    def test_semestres_diferentes(self):
        outro_semestre = SemestreLetivo.objects.create(nome="2027.1", ativo=True)
        outro_semestre.componentes.add(self.outro)
        with self.assertRaises(ValidationError):
            self.importar(receptor_id=self.outro.pk)

    def test_proprio_componente(self):
        with self.assertRaises(ValidationError):
            self.importar(receptor_id=self.doador.pk)

    def test_ids_duplicados_vazios_invalidos_e_limite(self):
        for ids in ([], [self.questao.pk] * 2, ["x"], [True], [0], list(range(1, 502))):
            with self.subTest(ids=str(ids)[:40]), self.assertRaises(ValidationError):
                self.importar(ids)

    def test_questao_de_outro_componente_rejeita_lote_inteiro(self):
        outra = self.nova_questao(componente=self.outro)
        with self.assertRaises(ValidationError):
            self.importar([self.questao.pk, outra.pk])
        self.assertFalse(Questao.objects.filter(componente=self.receptor).exists())

    def test_permissao_no_servico(self):
        self.usuario.is_staff = False
        self.usuario.save()
        with self.assertRaises(PermissionDenied):
            self.importar()

    def test_rollback_banco_e_arquivos_em_falha_no_segundo_item(self):
        outra = self.nova_questao()
        self.questao.imagem.save("original.png", ContentFile(b"imagem"), save=True)
        salvar = ImportacaoQuestao.objects.create
        contador = 0

        def falhar(**kwargs):
            nonlocal contador
            contador += 1
            if contador == 2:
                raise IntegrityError("falha simulada")
            return salvar(**kwargs)

        with patch.object(ImportacaoQuestao.objects, "create", side_effect=falhar):
            with self.assertRaises(IntegrityError):
                self.importar([self.questao.pk, outra.pk])
        self.assertFalse(Questao.objects.filter(componente=self.receptor).exists())
        self.assertFalse(ImportacaoQuestao.objects.exists())
        self.assertEqual(
            [p for p in Path(self.tmp.name).rglob("*") if p.is_file()],
            [Path(self.questao.imagem.path)],
        )

    def test_arquivo_ausente_reverte_todo_lote(self):
        outra = self.nova_questao(imagem="inexistente.png")
        with self.assertRaises(OSError):
            self.importar([self.questao.pk, outra.pk])
        self.assertFalse(Questao.objects.filter(componente=self.receptor).exists())

    def test_restricao_unica_no_banco(self):
        self.importar()
        with self.assertRaises(IntegrityError):
            from django.db import transaction

            with transaction.atomic():
                ImportacaoQuestao.objects.create(
                    origem=self.questao,
                    origem_identificador=self.questao.pk,
                    componente_origem="Doador",
                    copia=None,
                    receptor=self.receptor,
                    semestre=self.semestre,
                    responsavel=self.usuario,
                )
        self.assertEqual(ImportacaoQuestao.objects.count(), 1)

    def test_consultas_crescem_linearmente_sem_n_mais_um_de_alternativas(self):
        ids = [self.questao.pk] + [self.nova_questao().pk for _ in range(9)]
        self.usuario.get_all_permissions()
        from django.db import connection
        from django.test.utils import CaptureQueriesContext

        with CaptureQueriesContext(connection) as consultas:
            self.importar(ids)
        selects_alternativas = [
            q["sql"]
            for q in consultas
            if q["sql"].startswith("SELECT") and 'FROM "questoes_alternativa"' in q["sql"]
        ]
        self.assertEqual(len(selects_alternativas), 1)


class InterfaceImportacaoTests(DadosImportacao, TestCase):
    def test_acesso_anonimo_e_staff_sem_permissoes(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        usuario = get_user_model().objects.create_user("staff", password="teste", is_staff=True)
        self.client.force_login(usuario)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, {}).status_code, 403)

    def test_staff_com_permissoes_e_menu_proprio(self):
        usuario = get_user_model().objects.create_user("importador", is_staff=True)
        usuario.user_permissions.set(
            Permission.objects.filter(
                codename__in=["importar_questoes", "view_questao", "add_questao"]
            )
        )
        self.client.force_login(usuario)
        self.assertContains(self.client.get(reverse("admin:index")), self.url)
        pagina = self.pagina()
        confirmacao = self.postar(pagina)
        self.assertContains(confirmacao, "Confirmar importação")
        self.assertEqual(self.postar(confirmacao, "importar", []).status_code, 200)
        self.assertEqual(ImportacaoQuestao.objects.get().responsavel, usuario)

    def test_login_direto_retorna_ao_admin(self):
        self.client.logout()
        resposta = self.client.post(
            reverse("admin:login"), {"username": "admin", "password": "teste"}
        )
        self.assertRedirects(resposta, reverse("admin:index"))

    def test_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.usuario)
        self.assertEqual(client.post(self.url, self.contexto()).status_code, 403)

    def test_exibe_somente_semestres_ativos_e_receptores_validos(self):
        SemestreLetivo.objects.create(nome="2025.1", ativo=False)
        pagina = self.pagina()
        self.assertContains(pagina, "2026.2")
        self.assertNotContains(pagina, "2025.1")
        self.assertNotContains(pagina, "Fora do semestre")
        receptores = pagina.context["contexto_form"].fields["receptor"].queryset
        self.assertEqual(list(receptores), [self.receptor])

    def test_fluxo_confirmacao_e_reenvio(self):
        pagina = self.pagina()
        self.assertContains(pagina, "questoes/importacao.js")
        confirmacao = self.postar(pagina)
        self.assertContains(confirmacao, "Confirmar importação")
        self.assertEqual(Questao.objects.filter(componente=self.receptor).count(), 0)
        resultado = self.postar(confirmacao, "importar", [])
        self.assertContains(resultado, "1 importadas; 0 ignoradas (já importadas); 0 erros")
        reenvio = self.postar(confirmacao, "importar", [])
        self.assertContains(reenvio, "0 importadas; 1 ignoradas")

    def test_sem_confirmacao_e_troca_de_receptor_sao_rejeitados(self):
        pagina = self.pagina()
        self.assertEqual(self.postar(pagina, "importar").status_code, 400)
        confirmacao = self.postar(pagina)
        self.semestre.componentes.add(self.outro)
        self.assertEqual(
            self.postar(confirmacao, "importar", [], receptor=self.outro.pk).status_code, 400
        )

    def test_selecao_assinada_invalida_ou_de_outra_sessao(self):
        pagina = self.pagina()
        self.assertEqual(self.postar(pagina, estado="adulterado").status_code, 400)
        client = Client()
        client.force_login(self.usuario)
        self.assertEqual(
            client.post(
                self.url,
                dict(
                    self.contexto(receptor=self.receptor.pk),
                    estado=pagina.context["estado"],
                    acao="confirmar",
                    marcadas=[self.questao.pk],
                ),
            ).status_code,
            400,
        )

    def test_estado_expirado(self):
        with patch("django.core.signing.time.time", return_value=0):
            pagina = self.pagina()
        self.assertEqual(self.postar(pagina).status_code, 400)

    def test_ids_manipulados_inativos_e_semestre_trocado(self):
        pagina = self.pagina()
        outra = self.nova_questao(componente=self.outro)
        self.assertEqual(self.postar(pagina, marcadas=[outra.pk]).status_code, 400)
        self.assertEqual(
            self.postar(pagina, receptor=self.doador.pk).context["contexto_form"].is_valid(), False
        )
        outro_semestre = SemestreLetivo.objects.create(nome="2027.1", ativo=True)
        outro_semestre.componentes.add(self.doador, self.receptor)
        self.assertEqual(self.postar(pagina, semestre=outro_semestre.pk).status_code, 400)
        self.semestre.ativo = False
        self.semestre.save()
        self.assertFalse(self.postar(pagina).context["contexto_form"].is_valid())
        self.assertFalse(ImportacaoQuestao.objects.exists())

    def test_filtros_paginacao_e_selecao_conservada(self):
        outras = [self.nova_questao(enunciado=f"Questão extra {n}") for n in range(30)]
        pagina1 = self.pagina()
        self.assertEqual(len(pagina1.context["pagina_obj"]), 25)
        pagina2 = self.postar(pagina1, "pagina", pagina=2)
        self.assertEqual(pagina2.context["selecionadas"], {self.questao.pk})
        filtro = self.postar(pagina2, "filtrar", [outras[-1].pk], busca="Qual alternativa")
        self.assertEqual(filtro.context["selecionadas"], {self.questao.pk, outras[-1].pk})
        self.assertEqual(filtro.context["pagina_obj"].paginator.count, 1)
        confirmacao = self.postar(filtro, "confirmar", [])
        self.assertEqual(confirmacao.context["selecionadas"], {outras[-1].pk})
        self.postar(confirmacao, "importar", [])
        self.assertEqual(Questao.objects.filter(componente=self.receptor).count(), 1)

    def test_selecionar_todas_do_filtro_e_limpar_outras_paginas(self):
        for n in range(30):
            self.nova_questao(enunciado=f"Extra {n}")
        pagina = self.pagina()
        todas = self.postar(pagina, "selecionar_filtradas", [])
        self.assertEqual(len(todas.context["selecionadas"]), 31)
        limpa = self.postar(todas, "limpar_todas", [self.questao.pk])
        self.assertEqual(limpa.context["selecionadas"], set())
        filtradas = self.postar(limpa, "selecionar_filtradas", [], busca="Extra")
        self.assertEqual(len(filtradas.context["selecionadas"]), 30)

    def test_selecionar_todas_nao_ultrapassa_limite_e_rejeita_repetidas(self):
        Questao.objects.bulk_create(
            [
                Questao(componente=self.doador, enunciado=f"Extra {n}", justificativa="J")
                for n in range(500)
            ]
        )
        pagina = self.pagina()
        excesso = self.postar(pagina, "selecionar_filtradas", [])
        self.assertEqual(excesso.context["selecionadas"], set())
        self.assertContains(excesso, "Refine o filtro")
        self.assertEqual(self.postar(pagina, marcadas=[self.questao.pk] * 2).status_code, 400)

    def test_erros_de_storage_sao_explicitos_sem_importacao_parcial(self):
        pagina = self.pagina()
        confirmacao = self.postar(pagina)
        with patch(
            "questoes.importacao_admin.importar_questoes", side_effect=OSError("indisponível")
        ):
            with self.assertLogs("questoes.importacao_admin", level="ERROR"):
                resposta = self.postar(confirmacao, "importar", [])
        self.assertEqual(resposta.status_code, 503)
        self.assertContains(resposta, "Nenhuma questão foi importada", status_code=503)

    def test_importacao_apos_questao_excluida_rejeita_tudo(self):
        pagina = self.pagina()
        confirmacao = self.postar(pagina)
        self.questao.delete()
        self.assertEqual(self.postar(confirmacao, "importar", []).status_code, 400)

    def test_html_nao_executa_enunciado(self):
        self.questao.enunciado = "<script>alert(1)</script>"
        self.questao.save()
        pagina = self.pagina()
        self.assertNotContains(pagina, "<script>alert(1)</script>")
        self.assertContains(pagina, "&lt;script&gt;")

    def test_admin_auditoria_somente_leitura(self):
        self.importar()
        registro = ImportacaoQuestao.objects.get()
        self.assertEqual(
            self.client.get(reverse("admin:questoes_importacaoquestao_add")).status_code, 403
        )
        self.assertEqual(
            self.client.post(
                reverse("admin:questoes_importacaoquestao_delete", args=[registro.pk])
            ).status_code,
            403,
        )
        self.assertContains(
            self.client.get(reverse("admin:questoes_importacaoquestao_changelist")), self.url
        )

    def test_regressao_submissao_aprovacao_prova_e_gabarito(self):
        from django.contrib import admin
        from django.test import RequestFactory

        pedido = RequestFactory().get("/")
        pedido.user = self.usuario
        with patch.object(admin.site._registry[Questao], "message_user"):
            admin.site._registry[Questao].reprovar_questoes(
                pedido, Questao.objects.filter(pk=self.questao.pk)
            )
            self.questao.refresh_from_db()
            self.assertEqual(self.questao.status, "REPROVADA")
            admin.site._registry[Questao].aprovar_questoes(
                pedido, Questao.objects.filter(pk=self.questao.pk)
            )
        for nome in ("submeter_questao", "pagina_gerar_prova"):
            self.assertEqual(self.client.get(reverse(nome)).status_code, 200)
        prova = self.client.get(reverse("prova_gerada"), {"componentes": [self.doador.pk]})
        self.assertEqual(prova.status_code, 200)
        self.assertEqual(prova.context["questao_ids"], [self.questao.pk])
        self.assertEqual(
            self.client.get(reverse("prova_gabarito"), {"ids": str(self.questao.pk)}).status_code,
            200,
        )
        dados = dict(
            componente=self.receptor.pk,
            enunciado="Enviada",
            justificativa="Explicação",
            **{
                "form-TOTAL_FORMS": "2",
                "form-INITIAL_FORMS": "0",
                "form-MAX_NUM_FORMS": "5",
                "form-0-texto": "A",
                "form-0-eh_correta": "on",
                "form-1-texto": "B",
            },
        )
        self.assertEqual(self.client.post(reverse("submeter_questao"), dados).status_code, 302)
        self.assertEqual(Questao.objects.get(enunciado="Enviada").status, "PENDENTE")


class ConcorrenciaImportacaoTests(DadosImportacao, TransactionTestCase):
    def test_duas_operacoes_simultaneas_criam_uma_unica_copia(self):
        barreira = threading.Barrier(2)

        def executar():
            close_old_connections()
            try:
                usuario = get_user_model().objects.get(pk=self.usuario.pk)
                usuario.get_all_permissions()
                barreira.wait(timeout=15)
                return self.importar(usuario=usuario)
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(lambda _: executar(), range(2)))
        self.assertEqual(sorted((r.importadas, r.ignoradas) for r in resultados), [(0, 1), (1, 0)])
        self.assertEqual(Questao.objects.filter(componente=self.receptor).count(), 1)
        self.assertEqual(ImportacaoQuestao.objects.count(), 1)
