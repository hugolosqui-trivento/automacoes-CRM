import re
from playwright.sync_api import Playwright, sync_playwright, expect
from time import sleep
import pandas as pd

df = pd.read_csv('dataset.csv')


leads = df['ID Lead'].drop_duplicates().tolist()

def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()

    # login
    page.goto("https://wakeme.crmeducacional.com/login/index.html?returnUrl=%2Fapp%2Fleads%2Findex.html")
    page.get_by_role("textbox", name="E-mail").fill("arthurmadeira@triventoeducacao.com.br")
    page.get_by_role("textbox", name="Senha").fill("12345")
    page.get_by_role("button", name="Entrar").click()

    sleep(5)  # aguarda 5 segundos para garantir que a página carregue completamente


    # iterar sobre as leads e excluir inscrições
    for lead in leads:
        inscricoes = df.loc[df['ID Lead'] == lead, 'id_inscricao'].values
        for inscricao in inscricoes:
            if pd.isna(inscricao):
                continue  # pular se a inscrição for NaN
            try:
                link = page.goto(f"https://wakeme.crmeducacional.com/app/inscriptions/?open={inscricao}")
                sleep(3)  # aguarda 5 segundos para garantir que a página carregue completamente
                # link = f"https://wakeme.crmeducacional.com/app/inscriptions/?legacyUrl=%2FInscricao%2FEditar%{inscricao}"
                page.goto(link)
                

            except Exception as e:
                print(f"Erro ao acessar a inscrição {inscricao}: {e}")
                pass
            page.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame.get_by_role("button", name="Relacionados").click()

            
            localizadores = [
                "#botoes-leads-da-inscricao",
                "#botoes-pagamentos-da-inscricao",
                "#botoes-redacoes-da-inscricao",
                "#provas-objetivas-da-inscricao",
                '#avaliacoes-da-inscricao',
                '#classificacoes-da-inscricao',
                '#precos-da-inscricao',
                '#termos-da-inscricao']

            frame = page.locator("iframe[title=\"ConteÃºdo legado\"]").content_frame

            # for localizador in localizadores:
            #     section = frame.locator(localizador)
            #     # garantir que a seção esteja visível na viewport do iframe
            #     try:
            #         section.scroll_into_view_if_needed()
            #     except Exception:
            #         pass
            #     sleep(0.3)

            #     checkboxes = section.locator("input[type='checkbox']")
            #     try:
            #         count = checkboxes.count()
            #     except Exception:
            #         count = 0

            #     print(f"Encontrados {count} checkboxes na seção {localizador}.")
            #     # se não achar checkboxes, tente rolar mais dentro do iframe para carregar itens dinâmicos
                

            #     for i in range(count):
            #         cb = checkboxes.nth(i)
            #         try:
            #             if cb.is_visible():
            #                 try:
            #                     cb.check(timeout=2000)
            #                 except Exception:
            #                     try:
            #                         cb.click()
            #                     except Exception:
            #                         handle = cb.element_handle()
            #                         if handle:
            #                             try:
            #                                 handle.evaluate("el => { el.checked = true; el.dispatchEvent(new Event('change', {bubbles:true})); }")
            #                             except Exception:
            #                                 pass
                    
            #                 sleep(0.2)
            #         except Exception:
            #             # ignore individual checkbox errors and continue
            #             continue

                    

            #     sleep(1)
            #     # tentar remover itens desta seção se existir botão de delete
            #     try:
            #         delete_button = section.get_by_role("button", name="delete")
            #         if delete_button.is_visible():
            #             delete_button.click()
            #             sleep(1)
            #             confirm_button = frame.get_by_role("button", name="Remover")
            #             if confirm_button.is_visible():
            #                 confirm_button.click()
            #     except Exception:
            #         pass


            # adicionar uma confirmação manual para o usuário antes de clicar no botão "Excluir"
            print(f"Preparado para excluir a inscrição {inscricao}. Por favor, confirme manualmente se deseja prosseguir com a exclusão.")
            input("Pressione Enter para continuar...")  
        
            botao_excluir = frame.get_by_role("button", name="Excluir")
            sleep(3)  # aguarda 1 segundo para garantir que o botão seja clicado corretamente
            if botao_excluir.is_visible():
                botao_excluir.click(force=True)
                botao_confirmar_exclusao = page.get_by_role("button", name="Excluir")
                if botao_confirmar_exclusao.is_visible():
                    botao_confirmar_exclusao.click()
    
    
    
    # excluir lead
        try:
            page.goto(f"https://wakeme.crmeducacional.com/app/leads/edit/{lead}")
        except Exception as e:
            print(f"Erro ao acessar o lead {lead}: {e}")
            continue

        page.get_by_label("Confirmar exclusão").get_by_role("button", name="Excluir").click()
    

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
