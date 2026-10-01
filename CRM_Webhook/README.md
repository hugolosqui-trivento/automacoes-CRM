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
ngrok http 8000 --url https://thrift-swore-sappiness.ngrok-free.dev 
```

- API: <http://localhost:8000>
- Swagger: <http://localhost:8000/docs>
- Dashboard: <http://localhost:8501>
- Saúde: `GET /health`

## Docker Compose

O Compose executa três serviços mantendo as responsabilidades separadas:

```text
ngrok -> FastAPI -> Neon PostgreSQL <- Streamlit
```

FastAPI e Streamlit usam a mesma imagem do projeto, mas rodam como processos e
containers independentes. O Neon continua externo ao Compose.

1. Copie `.env.example` para `.env` e preencha `DATABASE_URL`,
   `NGROK_AUTHTOKEN` e `NGROK_URL`. Use a URL pooled do Neon com o driver
   `postgresql+psycopg://`.
2. Com o Docker Desktop em execução, inicie toda a stack:

```bash
docker compose up --build -d
docker compose ps
```

3. Acompanhe os logs e valide os serviços:

```bash
docker compose logs -f
curl http://127.0.0.1:8000/health
```

O dashboard fica em <http://127.0.0.1:8501>. A URL reservada configurada em
`NGROK_URL` encaminha requisições ao serviço `api` pela rede interna do Compose.
O token do ngrok e a conexão Neon permanecem somente no `.env`, que não entra
na imagem nem no Git.

Comandos operacionais:

```bash
docker compose stop
docker compose start
docker compose down
docker compose build --pull
```

`docker compose down` remove apenas os containers e a rede do Compose. Os dados
continuam no Neon.

### Testar o Dockerfile sem acessar o Neon

O procedimento abaixo valida a imagem usando um banco SQLite descartável dentro
de cada container. Assim, os testes de inicialização não executam a rotina de
retenção sobre o banco Neon configurado no `.env`.

Primeiro, valide o Dockerfile e a configuração do Compose:

```bash
docker build --check .
docker compose --env-file .env.example config --quiet
docker compose --env-file .env.example config --services
```

A lista de serviços esperada é:

```text
api
dashboard
ngrok
```

Construa a imagem local:

```bash
docker build -t crm-webhook:local .
```

Inicie containers temporários da API e do dashboard. As portas alternativas
`18000` e `18501` evitam conflito com processos locais nas portas padrão:

```bash
docker run --rm -d \
  --name crm-webhook-api-test \
  -e DATABASE_URL=sqlite:////tmp/crm_webhook.db \
  -p 127.0.0.1:18000:8000 \
  crm-webhook:local

docker run --rm -d \
  --name crm-webhook-dashboard-test \
  -e DATABASE_URL=sqlite:////tmp/crm_webhook.db \
  -p 127.0.0.1:18501:8501 \
  crm-webhook:local \
  streamlit run dashboard/app.py \
    --server.address=0.0.0.0 \
    --server.port=8501 \
    --server.headless=true
```

Confirme os health checks pelo host:

```bash
curl http://127.0.0.1:18000/health
curl http://127.0.0.1:18501/_stcore/health
```

Respostas esperadas:

```text
{"status":"ok"}
ok
```

Confirme também que os processos não executam como `root`:

```bash
docker exec crm-webhook-api-test id -u
docker exec crm-webhook-dashboard-test id -u
```

Os dois comandos devem retornar `10001`.

Para consultar os logs durante o diagnóstico:

```bash
docker logs crm-webhook-api-test
docker logs crm-webhook-dashboard-test
```

Ao terminar, remova somente os containers temporários:

```bash
docker rm -f crm-webhook-api-test crm-webhook-dashboard-test
```

Como eles foram iniciados com `--rm`, também serão removidos automaticamente se
forem encerrados normalmente. O arquivo SQLite fica em `/tmp` dentro de cada
container e desaparece com sua remoção.

Depois dessa validação isolada, teste a integração completa com Neon e ngrok:

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f
```

Esse último teste usa as credenciais reais do `.env`; confirme antes que
`DATABASE_URL`, `NGROK_AUTHTOKEN` e `NGROK_URL` estejam preenchidos corretamente.

### Publicar e executar a imagem em um servidor

Crie uma tag no seu registry e publique a mesma imagem usada pelos serviços:

```bash
docker build -t REGISTRY/crm-webhook:VERSION .
docker push REGISTRY/crm-webhook:VERSION
```

No servidor, copie `compose.yaml`, crie o `.env` fora do controle de versão e
defina nele:

```env
CRM_WEBHOOK_IMAGE=REGISTRY/crm-webhook:VERSION
ENVIRONMENT=production
```

Depois execute:

```bash
docker compose pull
docker compose up -d --no-build
```

Por padrão, as portas 8000 e 8501 são publicadas apenas em `127.0.0.1`. O ngrok
alcança a API diretamente pela rede interna. Só altere `DASHBOARD_BIND_ADDRESS`
para `0.0.0.0` se o servidor estiver protegido por firewall, proxy e
autenticação adequados, pois o painel contém dados pessoais.

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
