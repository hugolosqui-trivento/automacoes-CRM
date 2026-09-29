# Deploy de produção

Este guia publica os dois processos separadamente, mantendo a arquitetura do
projeto:

```text
CRM Educacional
      |
      | HTTPS POST /webhook
      v
Cloudflare (DNS, TLS e Tunnel)
      |
      | conexão privada do cloudflared
      v
FastAPI em uma VM na nuvem
      |
      v
Neon PostgreSQL
      ^
      |
Streamlit Community Cloud
```

O Streamlit Community Cloud hospeda somente `dashboard/app.py`. Ele não
hospeda o FastAPI nem o `cloudflared`. O conector do Cloudflare Tunnel precisa
rodar continuamente na mesma VM/rede do FastAPI.

## 1. Decisão recomendada

Para manter um Tunnel permanente, a opção mais simples é:

- dashboard: Streamlit Community Cloud;
- banco: Neon PostgreSQL;
- API: VM Linux permanente, preferencialmente Ubuntu 24.04 LTS;
- exposição da API: Cloudflare Tunnel nomeado e gerenciado pelo dashboard;
- processo da API: serviço `systemd` ouvindo apenas em `127.0.0.1:8000`;
- processo do Tunnel: `cloudflared` instalado como serviço.

Render, Railway, Cloud Run e serviços semelhantes já fornecem uma URL HTTPS
pública. Neles, normalmente se usa DNS/proxy da Cloudflare, sem Tunnel. Para
usar Tunnel nesses serviços seria necessário manter um `cloudflared` sidecar
sempre ativo, algo que depende da plataforma. Este guia usa uma VM porque o
modelo é previsível e compatível com um Tunnel permanente.

Não use uma URL temporária `trycloudflare.com` em produção.

## 2. Pontos encontrados na revisão

Antes do deploy, considere estes pontos do estado atual do projeto:

1. O projeto usa `psycopg[binary]`, isto é, Psycopg 3. Em ambiente limpo, a
   URL do SQLAlchemy deve começar com `postgresql+psycopg://`. A URL
   `postgresql+psycopg2://` presente em `.env.example` exige outro driver e
   pode falhar no Streamlit Community Cloud.
2. A API ainda não valida `WEBHOOK_SECRET`, HMAC ou token Bearer. Apenas criar
   essa variável de ambiente não protege nada, pois o código atual não a lê.
   O deploy funciona tecnicamente, mas o webhook não deve entrar em produção
   sem autenticação na aplicação ou uma restrição equivalente baseada nos
   IPs oficiais do CRM.
3. `GET /webhook/leads` e `GET /webhook/inscricoes` expõem dados pessoais e
   atualmente não exigem autenticação. O Streamlit não usa esses endpoints;
   ele consulta o Neon diretamente. Bloqueie essas rotas na borda ou implemente
   autenticação antes do uso público.
4. `/docs` e `/openapi.json` também ficam públicos no código atual. Bloqueie-os
   com Cloudflare Access/WAF ou desabilite-os em produção.
5. FastAPI e Streamlit executam `create_tables()` e a limpeza diária ao
   iniciar. Por isso, no estado atual, os dois precisam de permissões de DDL,
   `SELECT`, `INSERT`, `UPDATE` e `DELETE` no banco. Uma evolução recomendada é
   mover migrations e limpeza exclusivamente para o backend e dar acesso
   somente leitura ao Streamlit.
6. Não há Alembic. `create_all()` cria tabelas ausentes, mas não migra tabelas
   existentes quando colunas mudam. Adote migrations antes da primeira
   alteração de schema em produção.

## 3. Pré-requisitos

- repositório enviado ao GitHub, de preferência privado;
- permissão administrativa nesse repositório para conectá-lo ao Streamlit;
- projeto e branch de produção no Neon;
- uma VM Linux com IP de saída para internet;
- domínio gerenciado pela Cloudflare;
- conta Cloudflare Zero Trust;
- um hostname, por exemplo `api.seudominio.com`;
- acesso aos campos de configuração de webhook do CRM.

Nunca salve no GitHub a URL real do Neon, senha, token do Tunnel ou segredo do
webhook. `.env` e `.streamlit/secrets.toml` já estão ignorados pelo Git.

## 4. Validar o repositório antes de publicar

Na raiz do projeto:

```bash
uv sync --frozen
uv run pytest -q
uv run streamlit run dashboard/app.py
```

Em outro terminal:

```bash
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/health
```

A resposta esperada do health check é:

```json
{"status":"ok"}
```

O repositório possui `uv.lock`. O Streamlit Community Cloud reconhece esse
arquivo e o prioriza na instalação das dependências. Não é necessário criar
um `requirements.txt` duplicado.

## 5. Preparar o Neon

1. No console do Neon, abra **Connection Details** do branch de produção.
2. Ative **Pooled connection**. O hostname normalmente contém `-pooler`.
3. Copie a URL completa fornecida pelo Neon, incluindo os parâmetros TLS.
4. Para este projeto, ajuste somente o esquema para Psycopg 3:

```text
postgresql+psycopg://USUARIO:SENHA@HOST-POOLER/BANCO?sslmode=require&channel_binding=require
```

Use exatamente os parâmetros mostrados pelo Neon. Se a senha contiver `@`,
`/`, `:`, `#`, `%` ou outro caractere reservado, aplique URL encoding nela.

FastAPI e Streamlit devem receber a mesma `DATABASE_URL`. Escolha uma região
do Neon próxima da VM para reduzir a latência do webhook. O Streamlit
Community Cloud executa nos Estados Unidos, o que também deve ser considerado
na escolha da região.

O banco é criado/atualizado pelo startup atual da aplicação. Depois do
primeiro início, confirme no Neon a existência de:

- `webhook_events`;
- `leads`;
- `inscricoes`.

## 6. Publicar o FastAPI na VM

Os comandos abaixo assumem Ubuntu e o projeto em `/opt/crm-webhook`. Substitua
`URL_DO_REPOSITORIO` e `USUARIO_LINUX`.

### 6.1. Instalar ferramentas e baixar o projeto

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -LsSf https://astral.sh/uv/install.sh | sh
sudo mkdir -p /opt/crm-webhook
sudo chown USUARIO_LINUX:USUARIO_LINUX /opt/crm-webhook
git clone URL_DO_REPOSITORIO /opt/crm-webhook
cd /opt/crm-webhook
~/.local/bin/uv sync --frozen --no-dev
~/.local/bin/uv run pytest -q
```

Para repositório privado, use uma deploy key somente leitura ou outra
credencial de deploy do GitHub. Não copie seu token pessoal para arquivos do
repositório.

### 6.2. Criar o arquivo de ambiente

Crie `/etc/crm-webhook.env` fora do repositório:

```env
DATABASE_URL="postgresql+psycopg://USUARIO:SENHA@HOST-POOLER/BANCO?sslmode=require&channel_binding=require"
ENVIRONMENT="production"
LOG_LEVEL="INFO"
```

Proteja o arquivo, permitindo leitura pelo usuário do serviço:

```bash
sudo chown USUARIO_LINUX:USUARIO_LINUX /etc/crm-webhook.env
sudo chmod 600 /etc/crm-webhook.env
```

### 6.3. Criar o serviço systemd

Crie `/etc/systemd/system/crm-webhook-api.service`:

```ini
[Unit]
Description=CRM Webhook FastAPI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=USUARIO_LINUX
WorkingDirectory=/opt/crm-webhook
EnvironmentFile=/etc/crm-webhook.env
ExecStart=/opt/crm-webhook/.venv/bin/uvicorn api.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

O binding em `127.0.0.1` é intencional: a porta 8000 não deve ficar aberta
diretamente para a internet. O `cloudflared` acessará essa porta localmente.

Ative e teste:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now crm-webhook-api
sudo systemctl status crm-webhook-api
curl http://127.0.0.1:8000/health
sudo journalctl -u crm-webhook-api -n 100 --no-pager
```

Comece com um processo Uvicorn. Para o volume esperado de webhooks isso reduz
complexidade. Aumente workers somente após medir carga e revisar concorrência,
pool de conexões e a rotina de startup.

## 7. Criar o Cloudflare Tunnel permanente

Use um Tunnel **remotamente gerenciado**:

1. Acesse o dashboard Cloudflare Zero Trust.
2. Abra **Networking > Tunnels**.
3. Selecione **Create a tunnel** e escolha `cloudflared`.
4. Nomeie como `crm-webhook-production`.
5. Selecione Linux e a arquitetura da VM.
6. Copie e execute na VM o comando de instalação exibido pelo dashboard. O
   comando contém um token secreto semelhante a:

```bash
sudo cloudflared service install TOKEN_DO_TUNNEL
```

7. No Tunnel, abra **Routes**, adicione uma **Published application** e use:

```text
Hostname: api.seudominio.com
Service URL: http://localhost:8000
```

8. Confirme que o Tunnel aparece como **Healthy**.
9. Verifique o serviço e o endpoint público:

```bash
sudo systemctl status cloudflared
curl https://api.seudominio.com/health
```

O Tunnel inicia conexões de saída para a Cloudflare, normalmente pela porta
7844 TCP/UDP. Não abra a porta 8000 no firewall da VM. Mantenha apenas SSH (de
preferência restrito ao seu IP) e as conexões de saída necessárias.

O token do Tunnel concede capacidade de conectar um novo origin. Trate-o como
senha, não o coloque no repositório e rotacione-o se for exposto.

### Proteção das rotas na Cloudflare

O CRM precisa alcançar os `POST` abaixo sem uma tela interativa do Cloudflare
Access:

```text
POST /webhook
POST /webhook/lead
POST /webhook/inscricao
```

Não coloque login humano do Access na frente dessas rotas, a menos que o CRM
consiga enviar a credencial de serviço correspondente. Em vez disso:

- implemente segredo/HMAC na API;
- se o CRM publicar IPs fixos oficiais, permita somente esses IPs;
- configure rate limiting;
- limite tamanho de requisição;
- bloqueie métodos e caminhos que o CRM não utiliza.

Proteja ou bloqueie externamente:

```text
GET /webhook/leads
GET /webhook/inscricoes
GET /docs
GET /openapi.json
```

Mantenha `GET /health` acessível somente se ele for usado por monitoramento e
não inclua informações sensíveis na resposta.

## 8. Publicar o dashboard no Streamlit Community Cloud

1. Envie a versão validada para a branch de produção no GitHub.
2. Acesse <https://share.streamlit.io> e conecte a conta GitHub.
3. Selecione **Create app**.
4. Informe repositório, branch e o entrypoint:

```text
dashboard/app.py
```

5. Em **Advanced settings**, selecione Python 3.12, compatível com
   `requires-python = ">=3.11"` do projeto.
6. Em **Secrets**, adicione somente:

```toml
DATABASE_URL = "postgresql+psycopg://USUARIO:SENHA@HOST-POOLER/BANCO?sslmode=require&channel_binding=require"
```

7. Salve e faça o deploy.
8. Abra **Manage app > Logs** e confirme que dependências, conexão e tabelas
   carregaram sem erro.
9. Nas configurações do app, restrinja o acesso aos usuários autorizados. O
   painel contém dados pessoais e não deve ser público.

Não configure uma URL da API no Streamlit. O dashboard deste projeto consulta
o Neon diretamente, como previsto na arquitetura.

O Streamlit Community Cloud executa o app a partir da raiz do repositório. O
entrypoint em `dashboard/app.py` já adiciona a raiz ao `sys.path`, permitindo
importar `database` e `shared`.

## 9. Configurar o CRM

Use preferencialmente o endpoint genérico:

```text
https://api.seudominio.com/webhook
```

Ele identifica inscrições quando o payload contém
`cad_numeroinscricao`. Também existem endpoints explícitos:

```text
https://api.seudominio.com/webhook/lead
https://api.seudominio.com/webhook/inscricao
```

Configuração esperada:

```text
Método: POST
Content-Type: application/json
Resposta de sucesso: HTTP 202
X-Event-Id: identificador único do evento, quando disponível
```

O CRM deve enviar o evento do lead antes da inscrição relacionada. No modelo
atual, uma inscrição cujo Lead ainda não existe retorna `422`.

## 10. Teste ponta a ponta

Primeiro confirme infraestrutura:

```bash
curl -i https://api.seudominio.com/health
```

Envie um lead de teste com `createdon` do dia atual em UTC:

```bash
curl -i -X POST https://api.seudominio.com/webhook \
  -H 'Content-Type: application/json' \
  -H 'X-Event-Id: deploy-lead-001' \
  -d '{
    "leadid": "deploy-lead-001",
    "fullname": "Lead de validação",
    "createdon": "AAAA-MM-DDTHH:MM:SSZ"
  }'
```

Resposta esperada:

```json
{"status":"received","duplicate":false}
```

Depois:

1. confirme o evento e o lead no Neon;
2. aguarde até 10 segundos e confirme o lead no Streamlit;
3. reenvie exatamente o mesmo evento;
4. confirme `"duplicate": true` e ausência de duplicidade no banco;
5. envie uma inscrição relacionada ao mesmo `leadid`;
6. confirme a inscrição no Neon e no painel;
7. confira os logs do FastAPI e o estado **Healthy** do Tunnel.

Use dados fictícios nesse teste. A aplicação remove na inicialização os
registros fora do dia corrente de `America/Sao_Paulo`. Isso é comportamento
intencional deste projeto.

## 11. Operação e atualização

### Logs e diagnóstico

```bash
sudo journalctl -u crm-webhook-api -f
sudo journalctl -u cloudflared -f
sudo systemctl status crm-webhook-api
sudo systemctl status cloudflared
curl http://127.0.0.1:8000/health
curl https://api.seudominio.com/health
```

Monitore pelo menos:

- disponibilidade de `/health`;
- status do Tunnel;
- respostas HTTP `4xx` e `5xx`;
- eventos com `status = 'error'`;
- tempo desde o último webhook;
- conexões e consumo do Neon;
- reinicializações do serviço.

### Atualizar a API

Faça backup/snapshot quando a mudança envolver schema. Depois:

```bash
cd /opt/crm-webhook
git pull --ff-only
~/.local/bin/uv sync --frozen --no-dev
~/.local/bin/uv run pytest -q
sudo systemctl restart crm-webhook-api
sudo systemctl status crm-webhook-api
curl https://api.seudominio.com/health
```

O Streamlit Community Cloud acompanha commits da branch configurada e refaz o
deploy. Confira os logs depois de cada atualização.

Atualize o `cloudflared` periodicamente usando o gerenciador de pacotes pelo
qual ele foi instalado e reinicie o serviço. A Cloudflare mantém suporte para
versões recentes do conector.

## 12. Problemas comuns

### `No module named psycopg2`

A URL ainda usa `postgresql+psycopg2://`. Troque para
`postgresql+psycopg://`, pois o projeto instala Psycopg 3.

### Cloudflare retorna `502 Bad Gateway`

Na VM, teste:

```bash
curl http://127.0.0.1:8000/health
sudo systemctl status crm-webhook-api
sudo systemctl status cloudflared
```

Se o health local falhar, o problema está na API. Se funcionar localmente e
falhar no hostname, revise a Service URL do Tunnel e os logs do `cloudflared`.

### Streamlit não conecta ao Neon

- confira se o secret se chama exatamente `DATABASE_URL`;
- use a URL pooled com `postgresql+psycopg://`;
- preserve os parâmetros TLS fornecidos pelo Neon;
- verifique senha com URL encoding;
- confira os logs em **Manage app**;
- confirme que restrições de IP do Neon aceitam a origem. Os IPs de saída do
  Streamlit Community Cloud podem mudar.

### Inscrição retorna `422`

Confirme que o lead referenciado por `cad_clientepotencialid.Id` foi recebido
e persistido antes da inscrição.

### Registros antigos desapareceram

Esse é o comportamento configurado. FastAPI e Streamlit executam a retenção
diária ao iniciar, usando o fuso `America/Sao_Paulo`.

## 13. Checklist final

- [ ] testes locais aprovados;
- [ ] código enviado ao GitHub sem secrets;
- [ ] Neon de produção criado e URL pooled testada;
- [ ] URL usa `postgresql+psycopg://`;
- [ ] API executa como serviço e reinicia automaticamente;
- [ ] API escuta somente em `127.0.0.1:8000`;
- [ ] Tunnel nomeado aparece como **Healthy**;
- [ ] `https://api.seudominio.com/health` responde;
- [ ] webhook protegido por segredo/HMAC ou allowlist oficial do CRM;
- [ ] endpoints de leitura, Swagger e OpenAPI protegidos;
- [ ] Streamlit usa `dashboard/app.py` e Python 3.12;
- [ ] `DATABASE_URL` configurada nos Secrets do Streamlit;
- [ ] dashboard com acesso restrito;
- [ ] lead, inscrição e reenvio idempotente testados;
- [ ] logs e alertas configurados;
- [ ] procedimento de atualização e rollback registrado.

## Referências oficiais

- [Deploy no Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)
- [Dependências no Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Organização de arquivos no Streamlit Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/file-organization)
- [Configurações e acesso do app Streamlit](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/app-settings)
- [Criar Cloudflare Tunnel pelo dashboard](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/get-started/create-remote-tunnel/)
- [Instalar o cloudflared](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/downloads/)
- [FastAPI atrás de proxy](https://fastapi.tiangolo.com/advanced/behind-a-proxy/)
- [Workers do FastAPI/Uvicorn](https://fastapi.tiangolo.com/deployment/server-workers/)
- [Connection pooling no Neon](https://neon.com/docs/manage/endpoints/)
