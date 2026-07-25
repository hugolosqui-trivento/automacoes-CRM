import re
from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # login
    page.goto("https://wakeme.crmeducacional.com/login/index.html?returnUrl=%2Fapp%2Fleads%2Findex.html")
    page.get_by_role("textbox", name="E-mail").fill("arthurmadeira@triventoeducacao.com.br")
    page.get_by_role("textbox", name="Senha").fill("12345")
    page.get_by_role("button", name="Entrar").click()


    # acessando os leads
    page.get_by_role("link", name="group Candidatos").click()
    page.get_by_role("link", name="group Leads").click()


    # iterando sobre os leads
    page.get_by_role("searchbox", name="Filtrar por palavra-chave").click()
    page.get_by_role("searchbox", name="Filtrar por Celular, CPF, E-").fill("teste")
    page.get_by_role("searchbox", name="Filtrar por Celular, CPF, E-").press("Enter")

    with context.expect_page() as pagina:
        page.get_by_role("link", name="Analista Crm").click(modifiers=["ControlOrMeta"])


    page1 = pagina.value
    page1.get_by_role("button", name="Inscrições").click()

    with context.expect_page() as pagina2:
        page1.get_by_role("link", name="CAN-001144-TRI").click(modifiers=["ControlOrMeta"])

    page2 = pagina2.value
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Relacionados").click()
    
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-leads-da-inscricao").get_by_role("button", name="expand_more").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#leads-da-inscricao").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-leads-da-inscricao").get_by_role("button", name="delete").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Remover").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-pagamentos-da-inscricao").get_by_role("button", name="expand_more").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#pagamentos-da-inscricao").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-pagamentos-da-inscricao").get_by_role("button", name="delete").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Remover").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-redacoes-da-inscricao").get_by_role("button", name="expand_more").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#redacoes-da-inscricao").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#redacoes-da-inscricao").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-redacoes-da-inscricao").get_by_role("button", name="delete").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Remover").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#provas-objetivas-da-inscricao").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("row", name="Prova Objetiva Online - CAN-").get_by_role("checkbox").check()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-provas-objetivas-da-inscricao").get_by_role("button", name="delete").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Remover").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#avaliacoes-da-inscricao").click()
    page2.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="arrow_back_ios").click()
    page2.close()
    page1.get_by_role("link", name="CAN-001144-TRI").click(modifiers=["ControlOrMeta"])
    page3 = context.new_page()
    page3.goto("https://wakeme.crmeducacional.com/app/inscriptions/?open=b28bfd64-4149-f111-bec7-000d3a8928f0")
    page3.goto("https://wakeme.crmeducacional.com/app/inscriptions/?legacyUrl=%2FInscricao%2FEditar%2Fb28bfd64-4149-f111-bec7-000d3a8928f0")
    page3.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Relacionados").click()
    page3.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#avaliacoes-da-inscricao").click()
    page3.close()
    page1.get_by_role("link", name="CAN-001144-TRI").click(modifiers=["ControlOrMeta"])
    page4 = context.new_page()
    page4.goto("https://wakeme.crmeducacional.com/app/inscriptions/?open=b28bfd64-4149-f111-bec7-000d3a8928f0")
    page4.goto("https://wakeme.crmeducacional.com/app/inscriptions/?legacyUrl=%2FInscricao%2FEditar%2Fb28bfd64-4149-f111-bec7-000d3a8928f0")
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Relacionados").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("checkbox").check()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-avaliacoes-da-inscricao").get_by_role("button", name="delete").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Remover").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-classificacoes-da-inscricao").get_by_role("button", name="expand_more").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#classificacoes-da-inscricao").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-classificacoes-da-inscricao").get_by_role("button", name="delete").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Remover").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-precos-da-inscricao").get_by_role("button", name="expand_more").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#precos-da-inscricao").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator(".botoes-ribbon-tabela-json.remover-pagina-cad_preco-PrecosEspecificos").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Remover").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator("#botoes-termos-da-inscricao").get_by_role("button", name="expand_more").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator(".botoes-ribbon-tabela-json.remover-pagina-cad_termo-TermodeResponsabilidade").dblclick()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.locator(".botoes-ribbon-tabela-json.remover-pagina-cad_termo-TermodeResponsabilidade").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Remover").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Excluir").click()
    page4.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Excluir").click()
    page4.goto("https://wakeme.crmeducacional.com/app/inscriptions/?legacyUrl=%2FInscricao")
    page1.get_by_role("button", name="Excluir").click()
    page1.get_by_label("Confirmar exclusão").get_by_role("button", name="Excluir").click()
    page1.goto("https://wakeme.crmeducacional.com/app/leads/index.html")

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
