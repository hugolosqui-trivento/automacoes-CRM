import re
from playwright.sync_api import Playwright, sync_playwright, expect
from time import sleep

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://wakeme.crmeducacional.com/login/index.html?returnUrl=%2Fapp%2Findex.html")
    page.get_by_role("textbox", name="E-mail").fill("arthurmadeira@triventoeducacao.com.br")
    page.get_by_role("textbox", name="Senha").fill("12345")
    page.get_by_role("button", name="Entrar").click()
    sleep(5)  # aguarda 5 segundos para garantir que a página carregue completamente
    page.goto("https://wakeme.crmeducacional.com/app/inscriptions/?legacyUrl=%2FInscricao%2FEditar%2Fc05dba88-9363-f111-ab0c-6045bd39b70c")
    sleep(2)  # aguarda 5 segundos para garantir que a página carregue completamente
    relacionados = page.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Relacionados")
    relacionados.click()
    sleep(2)  # aguarda 5 segundos para garantir que a página carregue
    secoes = relacionados.locator("div.content.anime-left").all()
    print(f"Seções encontradas: {len(secoes)}")
    # procura por ckecks dentro de cada seção e marca todos os que encontrar
    for secao in secoes:
        checkboxes = secao.locator("input[type=\"checkbox\"]").all()
        for checkbox in checkboxes:
            checkbox.check()
    sleep(15)  # aguarda 5 segundos para garantir que a página carregue
    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
