
import re
from playwright.sync_api import Playwright, sync_playwright, expect
import pandas as pd
from time import sleep

df = pd.read_excel("base.xlsx")

df = df[df['Razão do Status'] == "Cancelado"]

leads = df["Lead"].drop_duplicates().tolist()





def run(playwright: Playwright) -> None:
    # login 
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://wakeme.crmeducacional.com/login/index.html?returnUrl=%2FHome%2FPrincipal")
    page.get_by_role("textbox", name="E-mail").fill("arthurmadeira@triventoeducacao.com.br")
    page.get_by_role("textbox", name="Senha").fill("12345")
    page.get_by_role("button", name="Entrar").click()

    sleep(5)
    

    # loop pelos leads

    for id_lead in leads:
        
        
        page.goto(f'https://wakeme.crmeducacional.com/app/leads/edit/{id_lead}')
        

        # Agora atua na nova página
        try:
            page.get_by_role("button", name="Reativar Lead", timeout=3000).click()
            page.get_by_role("button", name="Sim", timeout=3000).click()
        except:
            pass
        sleep(1)
        
    
    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
