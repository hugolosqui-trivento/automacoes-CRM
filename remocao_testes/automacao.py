import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

import pandas as pd
from playwright.sync_api import Playwright, expect, sync_playwright


BASE_URL = "https://wakeme.crmeducacional.com"
PASTA = Path(__file__).resolve().parent
ARQUIVO_INSCRICOES_PROCESSADAS = PASTA / "inscricoes_processadas.txt"
ARQUIVO_LEADS_PROCESSADOS = PASTA / "leads_processados.txt"
SECOES = (
    "leads", "pagamentos", "redacoes", "provas",
    "avaliacoes", "classificacoes", "precos", "termos",
)
TIMEOUT = 30_000
CHECKBOX_LINHA = "input.crm-data-grid__row-select"


def carregar_processados(arquivo):
    try:
        return set(Path(arquivo).read_text(encoding="utf-8").splitlines())
    except FileNotFoundError:
        return set()


def registrar_processado(arquivo, valor):
    with open(arquivo, "a", encoding="utf-8") as file:
        file.write(f"{valor}\n")


def carregar_dataset():
    df = pd.read_csv(PASTA / "dataset.csv", dtype=str, comment="#").fillna("")
    for coluna in ("ID Lead", "id_inscricao"):
        # Valida a base inteira antes de iniciar qualquer operação no CRM.
        df[coluna] = df[coluna].str.strip().map(
            lambda valor: str(UUID(valor)) if valor else ""
        )
    return df.loc[df["ID Lead"] != ""].drop_duplicates()


def resposta_do_endpoint(response, metodo, caminho):
    return (
        response.request.method == metodo
        and urlsplit(response.url).path.rstrip("/") == caminho.rstrip("/")
    )


def verificar_resposta(response, exigir_sucesso=False):
    if not response.ok:
        raise RuntimeError(f"CRM retornou HTTP {response.status}: {response.text()[:500]}")
    if response.status == 204:
        return
    try:
        dados = response.json()
    except ValueError as exc:
        raise RuntimeError("O CRM não retornou JSON; verifique a sessão de login.") from exc
    if not isinstance(dados, dict):
        raise RuntimeError(f"Resposta inesperada do CRM: {dados!r}")
    sucesso = dados.get("success", dados.get("Success"))
    if sucesso is False or dados.get("error") or (exigir_sucesso and sucesso is not True):
        raise RuntimeError(f"Operação rejeitada pelo CRM: {dados}")


def abrir_registro(page, entidade, registro_id):
    rota = "inscriptions" if entidade == "inscricoes" else "leads"
    endpoint = f"/api/v1/{entidade}/{registro_id}"
    with page.expect_response(
        lambda r: resposta_do_endpoint(r, "GET", endpoint), timeout=TIMEOUT
    ) as resposta:
        page.goto(f"{BASE_URL}/app/{rota}/edit/{registro_id}")
    verificar_resposta(resposta.value)
    expect(page.get_by_role("button", name="Excluir", exact=True)).to_be_visible()


def abrir_relacionados(page):
    aba = page.get_by_role("button", name="Relacionados", exact=True)
    if aba.is_visible():
        aba.click()
    else:
        page.get_by_role("button", name="Mais abas", exact=True).click()
        page.get_by_role("menuitem", name="Relacionados", exact=True).click()
    expect(page.locator('article[data-section="leads"]')).to_be_visible()


def aguardar_grade(page, secao, ids_anteriores=()):
    """Espera dados ou estado vazio; erros de carregamento nunca viram zero linhas."""
    page.wait_for_function(
        """({secao, anteriores}) => {
            const root = document.querySelector('article[data-section="' + secao + '"]');
            const visible = el => el && el.getClientRects().length > 0
                && getComputedStyle(el).visibility !== 'hidden';
            if (!root || visible(root.querySelector('.crm-data-grid__load-overlay')))
                return false;
            const erros = root.querySelectorAll('.crm-data-grid__error, .lead-rel-error');
            if ([...erros].some(el => visible(el) && el.textContent.trim())) return true;
            const ids = [...root.querySelectorAll('tbody tr[data-row-id]')]
                .map(el => el.dataset.rowId);
            if (ids.some(id => anteriores.includes(id))) return false;
            return ids.length > 0 || visible(root.querySelector('.lead-rel-empty'));
        }""",
        arg={"secao": secao, "anteriores": list(ids_anteriores)},
        timeout=TIMEOUT,
    )
    section = page.locator(f'article[data-section="{secao}"]')
    for erro in section.locator(".crm-data-grid__error, .lead-rel-error").all():
        if erro.is_visible() and erro.inner_text().strip():
            raise RuntimeError(f"Falha na seção {secao}: {erro.inner_text()}")
    return section


def selecionar_linhas(page, section):
    # O checkbox do cabeçalho é oculto. Marcar somente os inputs das linhas.
    checkboxes = section.locator(CHECKBOX_LINHA)
    ids = checkboxes.evaluate_all(
        "xs => xs.map(x => x.closest('tr').dataset.rowId)"
    )
    for checkbox in checkboxes.all():
        checkbox.check()
        expect(checkbox).to_be_checked()
    selecionados = page.evaluate(
        "() => window.EntityListRuntime.getGrid().getSelectedRowIds()"
    )
    if not ids or len(set(ids)) != len(ids) or set(selecionados) != set(ids):
        raise RuntimeError("A seleção interna da grade não corresponde às linhas marcadas.")
    return ids


def processar_secao(page, inscricao, secao, validar=False):
    section = page.locator(f'article[data-section="{secao}"]')
    toggle = section.locator("button.lead-rel-section__toggle")
    if toggle.get_attribute("aria-expanded") != "true":
        toggle.click()
    anteriores = ()
    vistos = set()
    total = 0
    while True:
        section = aguardar_grade(page, secao, anteriores)
        if section.locator(CHECKBOX_LINHA).count() == 0:
            break
        ids = selecionar_linhas(page, section)
        if vistos.intersection(ids):
            raise RuntimeError(f"A grade repetiu registros já processados em {secao}.")
        dialog = page.get_by_role("dialog").filter(
            has_text="Tem certeza que deseja remover o relacionamento?"
        )
        try:
            section.locator("button.lead-rel-btn-remover").click()
            expect(dialog).to_be_visible()
            confirmar = dialog.get_by_role("button", name="Remover", exact=True)
            expect(confirmar).to_be_enabled()
            if validar:
                dialog.get_by_role("button", name="Cancelar", exact=True).click()
            else:
                endpoint = f"/api/v1/inscricoes/{inscricao}/disassociate"
                with page.expect_response(
                    lambda r: resposta_do_endpoint(r, "POST", endpoint), timeout=TIMEOUT
                ) as resposta:
                    confirmar.click()
                verificar_resposta(resposta.value)
            expect(dialog).not_to_be_visible()
        finally:
            if dialog.is_visible():
                dialog.get_by_role("button", name="Cancelar", exact=True).click()
            if validar:
                for checkbox in section.locator(CHECKBOX_LINHA).all():
                    checkbox.uncheck()

        vistos.update(ids)
        total += len(ids)
        anteriores = ids
        if validar:
            proxima = section.locator("button.crm-data-grid__next")
            if proxima.count() == 0 or not proxima.is_enabled():
                break
            proxima.click()
        # Remover recria a grade na primeira página: continuar até ficar vazia,
        # sem avançar a página e pular registros que subiram após a remoção.
    acao = "validados" if validar else "desvinculados"
    print(f"  {secao}: {total} registro(s) {acao}.", flush=True)
    return total


def processar_relacionados(page, inscricao, validar=False):
    abrir_relacionados(page)
    return sum(processar_secao(page, inscricao, secao, validar) for secao in SECOES)


def excluir_registro(page, entidade, registro_id):
    page.get_by_role("button", name="Excluir", exact=True).click()
    dialog = page.get_by_role("dialog").filter(has_text="Confirmar exclusão")
    expect(dialog).to_be_visible()
    endpoint = f"/api/v1/{entidade}/{registro_id}"
    with page.expect_response(
        lambda r: resposta_do_endpoint(r, "DELETE", endpoint), timeout=TIMEOUT
    ) as resposta:
        dialog.get_by_role("button", name="Excluir", exact=True).click()
    verificar_resposta(resposta.value, exigir_sucesso=True)
    rota = "inscriptions" if entidade == "inscricoes" else "leads"
    page.wait_for_url(re.compile(rf"/app/{rota}/(?:index\.html)?(?:\?.*)?$"))


def run(playwright: Playwright, validar=False) -> None:
    df = carregar_dataset()
    inscricoes_processadas = carregar_processados(ARQUIVO_INSCRICOES_PROCESSADAS)
    leads_processados = carregar_processados(ARQUIVO_LEADS_PROCESSADOS)
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.set_default_timeout(TIMEOUT)
    falhas = []
    total = 0
    try:
        page.goto(f"{BASE_URL}/login/index.html")
        page.get_by_role("textbox", name="E-mail").fill("hugolosqui@triventoeducacao.com.br")
        page.get_by_role("textbox", name="Senha").fill("123")
        page.get_by_role("button", name="Entrar", exact=True).click()
        page.wait_for_url(re.compile(r"/app/"))

        for lead in df["ID Lead"].drop_duplicates():
            inscricoes = [i for i in df.loc[df["ID Lead"] == lead, "id_inscricao"].unique() if i]
            pendentes = [i for i in inscricoes if validar or i not in inscricoes_processadas]
            if not validar and lead in leads_processados and not pendentes:
                continue
            try:
                for inscricao in pendentes:
                    print(f"Inscrição {inscricao}:", flush=True)
                    abrir_registro(page, "inscricoes", inscricao)
                    total += processar_relacionados(page, inscricao, validar)
                    if validar:
                        continue
                    
                    excluir_registro(page, "inscricoes", inscricao)
                    registrar_processado(ARQUIVO_INSCRICOES_PROCESSADAS, inscricao)
                    inscricoes_processadas.add(inscricao)

                if validar:
                    if not inscricoes:
                        print(f"Lead {lead}: sem inscrição informada; nada a validar.", flush=True)
                    continue
                if lead not in leads_processados:
                    abrir_registro(page, "leads", lead)
                    excluir_registro(page, "leads", lead)
                    registrar_processado(ARQUIVO_LEADS_PROCESSADOS, lead)
                    leads_processados.add(lead)
            except Exception as exc:
                # Uma falha na inscrição impede a exclusão do lead correspondente.
                falhas.append(lead)
                print(f"ERRO no lead {lead}: {exc}", flush=True)
        print(f"Total de relacionamentos {'validados' if validar else 'removidos'}: {total}", flush=True)
    finally:
        context.close()
        browser.close()
    if falhas:
        raise RuntimeError(f"Falha em {len(falhas)} lead(s): {', '.join(falhas)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove relacionamentos, inscrições e leads do dataset.csv.")
    parser.add_argument(
        "--validar", action="store_true",
        help="Marca linhas e cancela confirmações; não exclui dados nem altera os arquivos de processados.",
    )
    args = parser.parse_args()
    with sync_playwright() as playwright:
        run(playwright, validar=args.validar)
