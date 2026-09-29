# CRM Webhook

Recepção auditável e idempotente de leads do CRM com FastAPI, persistência em PostgreSQL e painel operacional Streamlit.

```text
CRM -> POST /webhook -> FastAPI -> PostgreSQL <- Streamlit
```

## Configuração

1. Copie `.env.example` para `.env`.
2. Preencha `DATABASE_URL` com a conexão PostgreSQL/Neon.
3. Instale as dependências com `uv sync`.

Sem `DATABASE_URL`, o ambiente local usa `sqlite:///./crm_webhook.db`. Essa opção é apenas uma conveniência de desenvolvimento; produção deve usar PostgreSQL. O arquivo legado `leads.db` não é alterado.

## Execução

Em terminais separados:

```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
uv run streamlit run dashboard/app.py
```

- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- Dashboard: <http://localhost:8501>
- Saúde: `GET /health`

## Teste de envio de Lead e inscrição

Os exemplos abaixo usam PowerShell. Primeiro, envie um Lead:

```powershell
$leadBody = @{
    leadid = "lead-003"
    fullname = "Arthur Teste"
    emailaddress1 = "lead.teste@example.com"
    mobilephone = "(12) 99999-9999"
    cad_concursoatual = @{
        Id = "concurso-001"
        Name = "Vestibular 2027.1"
    }
    cad_situacaofunil = @{
        Value = 1
    }
    createdon = "2026-09-29T12:00:00Z"
} | ConvertTo-Json -Depth 4

Invoke-RestMethod `
    -Uri "http://localhost:8000/webhook" `
    -Method Post `
    -ContentType "application/json" `
    -Headers @{ "X-Event-Id" = "lead-evento-002" } `
    -Body $leadBody
```

Em seguida, envie uma inscrição relacionada ao mesmo Lead. O valor de
`cad_clientepotencialid.Id` deve ser igual ao `leadid` enviado anteriormente:

```powershell
$inscricaoBody = @{
    cad_clientepotencialid = @{
        Id = "lead-003"
        Name = "Arthur Teste"
    }
    cad_numeroinscricao = "INS-003"
    cad_situacao = @{
        Value = 1
    }
    cad_ofertaid = @{
        Name = "Administração"
    }
    crmeduc_linha_de_negocios = @{
        Name = "Vestibular"
    }
    trivento_unidadedeensinotrivento = @{
        Name = "Lorena"
    }
    createdon = "2026-09-29T12:05:00Z"
    modifiedon = "2026-09-29T12:05:00Z"
} | ConvertTo-Json -Depth 4

Invoke-RestMethod `
    -Uri "http://localhost:8000/webhook" `
    -Method Post `
    -ContentType "application/json" `
    -Headers @{ "X-Event-Id" = "inscricao-evento-002" } `
    -Body $inscricaoBody
```

Os dois endpoints respondem com HTTP `202 Accepted` e:

```json
{
  "status": "received",
  "duplicate": false
}
```

`X-Event-Id` é recomendado e deve ser único para cada novo evento. Para repetir o
teste como um novo envio, altere os dois valores de `X-Event-Id` e mantenha o
mesmo `leadid` em `cad_clientepotencialid.Id`. Se o cabeçalho e `event_id`
estiverem ausentes, a API deriva uma chave SHA-256 do payload. Reenvios do mesmo
evento não duplicam dados, e eventos novos fazem upsert do lead.

O endpoint legado `POST /webhook/lead` permanece disponível. O endpoint
`POST /webhook/inscricao` recebe inscrições explicitamente, enquanto
`POST /webhook` identifica inscrições pela presença de `cad_numeroinscricao`.
As consultas operacionais estão disponíveis em `GET /webhook/leads?limit=50`
e `GET /webhook/inscricoes?limit=50`, com limite máximo de 100 registros.

## Campos do CRM

Os campos do payload de criação do lead são normalizados assim:

| CRM | Campo interno / painel |
| --- | --- |
| `leadid` | Lead ID |
| `fullname` | Nome |
| `emailaddress1` | Email |
| `mobilephone` | Celular |
| `cad_concursoatual.Name` | Concurso |
| `cad_situacaofunil.Value` | Situação no funil |

O timestamp `createdon`, quando enviado, é armazenado como a data de criação do lead. O payload completo continua preservado para auditoria.

Os eventos de inscrição são armazenados na tabela `inscricoes`, relacionada a
`leads` por `cad_clientepotencialid.Id`. Os campos normalizados são:

| CRM | Campo interno / painel |
| --- | --- |
| `cad_clientepotencialid.Id` | Lead ID |
| `cad_numeroinscricao` | Número da inscrição |
| `cad_situacao.Value` | Situação no funil (1 a 6) |
| `cad_ofertaid.Name` | Curso |
| `crmeduc_linha_de_negocios.Name` | Forma de ingresso |
| `trivento_unidadedeensinotrivento.Name` | Unidade |

Na unidade, o prefixo `Faculdade Serra Dourada` é removido. O dashboard combina
a situação do Lead e das inscrições para mostrar um funil cumulativo da coorte
de Leads criados no dia, no fuso `America/Sao_Paulo`.

## Testes

```bash
uv run pytest -q
```

Os testes cobrem payload válido, JSON inválido, identificador ausente,
duplicidade, campos opcionais, falha do banco, normalização de inscrições e o
cálculo do funil diário.
