# Relatórios de captação em Streamlit

Dashboard interno para acompanhar leads sem proprietário e reconciliar matrículas entre o CRM Educacional e a planilha operacional.

## Preparação local no PowerShell

```powershell
cd app_relatorios
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Preencha `.streamlit/secrets.toml` com as credenciais, `MATRICULAS_URL` para a
planilha operacional e `MATRICULAS_MEDICINA_URL` para a planilha exclusiva de
Medicina. Para a correção das redações, informe também `OPENROUTER_KEY`; o
`OPENROUTER_MODEL` é opcional e usa `openai/gpt-4o-mini` por padrão. Esse arquivo
está ignorado pelo Git.

## Execução e testes

```powershell
python -m pytest
streamlit run app.py
```

O navegador abrirá a página de leads sem proprietário. As consultas ficam em cache por 15 minutos; o botão **Atualizar dados agora** invalida o cache e cria uma nova fotografia comum a todas as páginas.

## Regras aplicadas

- Somente inscrições com situação `Matriculado`.
- A comparação geral continua excluindo Medicina.
- A página de Medicina usa sua planilha exclusiva e considera somente inscrições
  matriculadas cujo curso seja `Medicina`.
- A conferência do CSV do Power BI combina as matrículas gerais e de Medicina do
  CRM e aceita unidades como `Medicina - Lorena` e `Medicina - Altamira`.
- Formas de ingresso que contenham `Cursos Livres` ou `PAGAMENTO / INTEGRAÇÃO TOTVS` são excluídas.
- Números de inscrição são aparados, convertidos para maiúsculas e consolidados como únicos.
- Inscrições e leads são relacionados pelo ID do lead (`cad_clientepotencialid.#text` × `leadid`); chaves e diferenças de caixa são normalizadas.
- O número de inscrição continua sendo a chave da reconciliação entre CRM e cada
  uma das planilhas.
- A unidade do lead prioriza `Unidade 1` e usa `Unidade 2` quando a primeira está vazia.
- As unidades são padronizadas como `Canaã`, `Lorena`, `Itabirito` ou `Altamira`; prefixos como `Medicina -` não aparecem no resultado.
- Na comparação de matrículas, o CRM usa a unidade do lead relacionado pelo ID e a planilha usa sua própria coluna `Unidade`; o filtro afeta os cards e os registros exclusivos, mas não as duplicidades.
- Duplicidades permanecem disponíveis na aba de qualidade.
- Inscrição sem lead e lead sem proprietário são ocorrências diferentes.
- Consultores ignorados não entram em casos acionáveis nem em divergências.
- Proprietários sem mapeamento são exibidos, nunca descartados silenciosamente.
- A página **Corrigir redações** consulta somente redações entregues, aplica a
  correção por IA e disponibiliza o resultado final em Excel.

Os mapeamentos e listas de exclusão ficam em `config/regras.py`.

## Publicação e controle de acesso

Configure `APP_ENV = "production"` e uma `APP_PASSWORD` forte nos secrets da plataforma. Sem essa senha, a aplicação recusa inicialização em modo de produção.

A senha compartilhada é uma barreira básica para uma instalação interna pequena. Como as tabelas contêm dados pessoais, a implantação definitiva deve preferir uma plataforma privada com SSO, controle individual de usuários, HTTPS e registro de acesso. Não publique o app anonimamente.

Para Streamlit Community Cloud, informe os mesmos campos de `secrets.toml.example` na área **Secrets** do app e defina `app_relatorios/app.py` como arquivo principal. Para infraestrutura corporativa, execute `streamlit run app.py` atrás do proxy autenticado da organização.

## Dependências e isolamento

Todas as dependências estão em `app_relatorios/requirements.txt`. O ambiente `.venv` fica dentro da pasta do app e não interfere nos scripts ou notebooks existentes.

