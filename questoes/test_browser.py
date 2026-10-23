"""Fluxo real no Chromium com dados sintéticos, habilitado explicitamente."""

import os
from unittest import skipUnless

from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from .models import Questao
from .tests import DadosImportacao


@skipUnless(
    os.environ.get("RUN_BROWSER_TESTS") == "1", "Habilite RUN_BROWSER_TESTS=1 para Chromium"
)
class BrowserImportacaoTests(DadosImportacao, StaticLiveServerTestCase):
    def test_selecao_js_filtro_paginacao_confirmacao_e_importacao(self):
        from playwright.sync_api import sync_playwright

        for n in range(30):
            self.nova_questao(enunciado=f"Questão extra {n}")
        with sync_playwright() as playwright:
            navegador = playwright.chromium.launch(
                headless=True,
                executable_path=os.environ.get("BROWSER_EXECUTABLE") or None,
            )
            pagina = navegador.new_page(viewport={"width": 1440, "height": 1100})
            erros = []
            pagina.on("pageerror", lambda erro: erros.append(str(erro)))
            pagina.goto(f"{self.live_server_url}/admin/login/")
            pagina.locator("[name=username]").fill("admin")
            pagina.locator("[name=password]").fill("teste")
            pagina.locator("[type=submit]").click()
            pagina.wait_for_url(f"{self.live_server_url}/admin/")
            pagina.get_by_role(
                "link", name="Importação de Questões entre Componentes", exact=True
            ).first.click()
            pagina.locator("[name=semestre]").select_option(str(self.semestre.pk))
            pagina.get_by_role("button", name="Carregar componentes / questões").click()
            pagina.locator("[name=doador]").select_option(str(self.doador.pk))
            pagina.get_by_role("button", name="Carregar componentes / questões").click()
            self.assertEqual(pagina.locator("[name=marcadas]").count(), 25)
            pagina.get_by_role("button", name="Selecionar todas desta página", exact=True).click()
            self.assertEqual(pagina.locator("#contador-selecao").inner_text(), "25 selecionadas")
            pagina.locator("[name=receptor]").select_option(str(self.receptor.pk))
            pagina.locator("[name=pagina]").fill("2")
            pagina.get_by_role("button", name="Ir e manter seleção", exact=True).click()
            pagina.locator("[name=marcadas]").last.check()
            self.assertEqual(pagina.locator("#contador-selecao").inner_text(), "26 selecionadas")
            pagina.locator("[name=busca]").fill("Qual alternativa")
            pagina.get_by_role("button", name="Filtrar e manter seleção").click()
            self.assertEqual(pagina.locator("[name=marcadas]").count(), 1)
            self.assertTrue(pagina.locator("[name=marcadas]").is_checked())
            self.assertEqual(pagina.locator("#contador-selecao").inner_text(), "26 selecionadas")
            pagina.get_by_role("button", name="Revisar importação").click()
            self.assertIn("26 questões selecionadas", pagina.locator(".importacao").inner_text())
            captura = os.environ.get("BROWSER_SCREENSHOT")
            if captura:
                pagina.screenshot(path=captura, full_page=True)
            pagina.get_by_role("button", name="Importar questões", exact=True).click()
            self.assertIn("26 importadas; 0 ignoradas", pagina.locator(".importacao").inner_text())
            self.assertEqual(erros, [])
            navegador.close()
        self.assertEqual(
            Questao.objects.filter(componente=self.receptor, status="PENDENTE").count(), 26
        )
        self.assertEqual(
            Questao.objects.filter(componente=self.doador, status="APROVADA").count(), 31
        )
