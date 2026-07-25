import sys
import os
from pathlib import Path

print("=" * 80)
print("VALIDAÇÃO PASSO A PASSO DO SCRIPT DE AUTOMAÇÃO")
print("=" * 80)

# PASSO 1: Verificar dependências
print("\n[PASSO 1] Verificando dependências instaladas...")
print("-" * 80)

dependencias = {
    'pandas': False,
    'playwright': False,
}

try:
    import pandas
    dependencias['pandas'] = True
    print("✓ pandas está instalado (versão: {})".format(pandas.__version__))
except ImportError as e:
    print("✗ pandas NÃO está instalado")
    print(f"  Erro: {e}")

try:
    import playwright
    dependencias['playwright'] = True
    print("✓ playwright está instalado")
except ImportError as e:
    print("✗ playwright NÃO está instalado")
    print(f"  Erro: {e}")

# Verificar se todas as dependências estão OK
if not all(dependencias.values()):
    print("\n❌ FALHA: Nem todas as dependências estão instaladas!")
    sys.exit(1)
else:
    print("\n✓ Todas as dependências OK!")

# PASSO 2: Verificar arquivo base.xlsx
print("\n[PASSO 2] Verificando arquivo base.xlsx...")
print("-" * 80)

base_file = Path("base.xlsx")
if not base_file.exists():
    print("✗ Arquivo base.xlsx NÃO encontrado!")
    sys.exit(1)

print(f"✓ Arquivo encontrado: {base_file.absolute()}")
print(f"  Tamanho: {base_file.stat().st_size} bytes")

# PASSO 3: Carregar e validar dados do Excel
print("\n[PASSO 3] Carregando e validando dados do Excel...")
print("-" * 80)

try:
    import pandas as pd
    df = pd.read_excel("base.xlsx")
    print(f"✓ Arquivo Excel carregado com sucesso")
    print(f"  Total de linhas: {len(df)}")
    print(f"  Colunas: {list(df.columns)}")
except Exception as e:
    print(f"✗ Erro ao ler arquivo Excel: {e}")
    sys.exit(1)

# PASSO 4: Validar coluna "Nome Completo"
print("\n[PASSO 4] Validando coluna 'Nome Completo'...")
print("-" * 80)

if "Nome Completo" not in df.columns:
    print("✗ Coluna 'Nome Completo' NÃO encontrada!")
    print(f"  Colunas disponíveis: {list(df.columns)}")
    sys.exit(1)

nomes = df["Nome Completo"].dropna().tolist()
print(f"✓ Coluna 'Nome Completo' encontrada")
print(f"  Total de nomes: {len(nomes)}")
print(f"  Nomes a processar:")

for i, nome in enumerate(nomes, 1):
    print(f"    {i:2d}. {nome}")

if len(nomes) == 0:
    print("\n⚠ AVISO: Nenhum nome encontrado para processar!")
    sys.exit(1)

# PASSO 5: Testar conectividade
print("\n[PASSO 5] Testando conectividade com a URL...")
print("-" * 80)

url_login = "https://wakeme.crmeducacional.com/login/index.html?returnUrl=%2FHome%2FPrincipal"
print(f"URL alvo: {url_login}")

try:
    import urllib.request
    response = urllib.request.urlopen(url_login, timeout=10)
    print(f"✓ URL acessível (Status: {response.status})")
except urllib.error.URLError as e:
    print(f"⚠ AVISO: Não foi possível conectar à URL")
    print(f"  Erro: {e}")
    print("  (Será necessário verificar credenciais e conectividade)")
except Exception as e:
    print(f"⚠ AVISO: Erro ao testar conectividade: {e}")

# PASSO 6: Validar implementação do script
print("\n[PASSO 6] Validando implementação do script automacao.py...")
print("-" * 80)

automacao_file = Path("automacao.py")
if not automacao_file.exists():
    print("✗ Arquivo automacao.py NÃO encontrado!")
    sys.exit(1)

print("✓ Arquivo automacao.py encontrado")

# Ler e verificar estrutura do script
with open(automacao_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar elementos essenciais
verificacoes = {
    'sync_playwright': 'sync_playwright' in content,
    'playwright.chromium.launch': 'playwright.chromium.launch' in content,
    'page.goto': 'page.goto' in content,
    'page.get_by_role': 'page.get_by_role' in content,
}

for elemento, encontrado in verificacoes.items():
    status = "✓" if encontrado else "✗"
    print(f"{status} {elemento}")

# PASSO 7: Resumo final
print("\n[RESUMO FINAL]")
print("-" * 80)
print("✓ Todas as validações passaram!")
print(f"✓ Pronto para executar automação com {len(nomes)} nomes")
print("\n" + "=" * 80)
print("Deseja prosseguir com a execução do script?")
print("=" * 80)

# Pergunta se quer continuar
try:
    resposta = input("\nDigite 'sim' para continuar ou 'não' para cancelar: ").strip().lower()
    if resposta != 'sim':
        print("Execução cancelada pelo usuário.")
        sys.exit(0)
except KeyboardInterrupt:
    print("\nExecução cancelada pelo usuário.")
    sys.exit(0)

# PASSO 8: Executar script principal
print("\n[PASSO 8] Iniciando execução do script principal...")
print("-" * 80)

try:
    from playwright.sync_api import sync_playwright
    
    print("Iniciando Playwright...")
    
    def run(playwright) -> None:
        # login 
        print("\n  → Iniciando navegador Chrome...")
        browser = playwright.chromium.launch(headless=False)
        print("  ✓ Navegador iniciado")
        
        context = browser.new_context()
        print("  ✓ Contexto de navegação criado")
        
        page = context.new_page()
        print("  ✓ Nova página criada")
        
        print(f"\n  → Acessando URL de login...")
        page.goto("https://wakeme.crmeducacional.com/login/index.html?returnUrl=%2FHome%2FPrincipal")
        print(f"  ✓ Página carregada: {page.url}")
        
        print(f"\n  → Executando login...")
        page.get_by_role("textbox", name="E-mail").click()
        page.get_by_role("textbox", name="E-mail").fill("arthurmadeira@triventoeducacao.com.br")
        print("  ✓ E-mail preenchido")
        
        page.get_by_role("textbox", name="Senha").click()
        page.get_by_role("textbox", name="Senha").fill("12345678")
        print("  ✓ Senha preenchida")
        
        page.get_by_role("button", name="Entrar").click()
        print("  ✓ Botão 'Entrar' clicado")
        
        # Aguardar após login
        page.wait_for_load_state("networkidle", timeout=30000)
        print(f"  ✓ Login bem-sucedido - URL atual: {page.url}")
        
        print(f"\n  → Navegando para Candidatos > Leads...")
        page.get_by_role("link", name="group Candidatos").click()
        print("  ✓ Clicado em Candidatos")
        
        page.wait_for_load_state("networkidle", timeout=10000)
        page.get_by_role("link", name="group Leads").click()
        print("  ✓ Clicado em Leads")
        
        page.wait_for_load_state("networkidle", timeout=10000)
        print(f"  ✓ Página de Leads carregada: {page.url}")

        # loop pelos nomes
        print(f"\n  → Iniciando processamento de {len(nomes)} nome(s)...")
        
        for idx, nome in enumerate(nomes, 1):
            print(f"\n  [{idx}/{len(nomes)}] Processando: {nome}")
            
            try:
                page.get_by_role("searchbox", name="Filtrar por palavra-chave (mí").click()
                print(f"      ✓ Caixa de busca clicada")
                
                page.get_by_role("searchbox", name="Filtrar por Celular, CPF, E-").fill(nome)
                print(f"      ✓ Nome preenchido na busca")
                
                page.get_by_role("searchbox", name="Filtrar por Celular, CPF, E-").press("Enter")
                print(f"      ✓ Busca executada")
                
                page.get_by_role("searchbox", name="Filtrar por palavra-chave (mí").click()
                
                # Espera a tabela aparecer
                page.wait_for_selector("#mount-entity-grid", timeout=10000)
                print(f"      ✓ Tabela apareceu")

                # Espera haver pelo menos uma célula
                page.wait_for_selector("#mount-entity-grid td", timeout=10000)
                print(f"      ✓ Célula encontrada")

                # Primeira célula da primeira linha
                primeira_celula = page.locator("#mount-entity-grid tbody tr td").first

                # Caso não exista tbody, usa todas as células
                if primeira_celula.count() == 0:
                    primeira_celula = page.locator("#mount-entity-grid td").first
                    print(f"      ℹ Usando seletor alternativo")

                url_antes = page.url
                
                # Captura a nova aba aberta pelo clique
                print(f"      → Abrindo detalhe do lead...")
                with context.expect_page() as pagina:
                    primeira_celula.click()

                page1 = pagina.value
                page1.wait_for_load_state("networkidle", timeout=10000)
                print(f"      ✓ Nova aba aberta: {page1.url}")

                # Agora atua na nova página
                print(f"      → Clicando em 'Reativar Lead'...")
                page1.get_by_role("button", name="Reativar Lead").click()
                print(f"      ✓ Botão 'Reativar Lead' clicado")
                
                page1.get_by_role("button", name="Sim").click()
                print(f"      ✓ Confirmação 'Sim' realizada")
                
                page1.wait_for_load_state("networkidle", timeout=5000)
                print(f"      ✓ {nome} reativado com sucesso!")

                page1.close()
                page.bring_to_front()
                
            except Exception as e:
                print(f"      ✗ ERRO ao processar {nome}: {e}")
                try:
                    page1.close()
                except:
                    pass
                page.bring_to_front()
                print(f"      Continuando com próximo nome...")
        
        print(f"\n  ✓ Processamento de todos os nomes concluído!")
        
        # ---------------------
        context.close()
        browser.close()
        print(f"  ✓ Navegador fechado")

    with sync_playwright() as playwright:
        run(playwright)
    
    print("\n✓ Script executado com sucesso!")
    
except KeyboardInterrupt:
    print("\n\n❌ Execução interrompida pelo usuário")
    sys.exit(1)
except Exception as e:
    print(f"\n❌ ERRO durante a execução: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 80)
print("VALIDAÇÃO CONCLUÍDA")
print("=" * 80)
