# Deploy local no Windows

Este guia executa o FastAPI e o Streamlit em um computador Windows da empresa,
com inicialização automática às **07:00** e encerramento às **20:00**.

```text
CRM Educacional
      |
      | HTTPS POST /webhook
      v
Cloudflare Tunnel
      |
      v
FastAPI no Windows (127.0.0.1:8000)
      |
      v
PostgreSQL local ou Neon
      ^
      |
Streamlit no Windows (porta 8501)
```

O Streamlit continua sendo somente o painel. O FastAPI continua sendo o único
receptor dos webhooks, e os dois processos compartilham o banco de dados.

## 1. Decisão sobre o horário de funcionamento

Desligar **FastAPI e Cloudflare Tunnel** às 20:00 torna o webhook indisponível
até as 07:00. Eventos enviados nesse intervalo somente serão recuperados se o
CRM fizer retentativas.

Antes de aplicar a agenda, confirme com o fornecedor do CRM:

- se eventos podem ser enviados entre 20:00 e 07:00;
- por quanto tempo e em quais códigos HTTP o CRM tenta novamente;
- se existe uma fila ou opção de reprocessamento manual.

Há dois modos possíveis:

1. **Recomendado:** FastAPI, PostgreSQL e Tunnel ficam ativos 24 horas; apenas o
   Streamlit funciona das 07:00 às 20:00.
2. **Horário solicitado:** FastAPI, Streamlit e Tunnel funcionam das 07:00 às
   20:00. Use este modo somente se a perda/retentativa fora do horário estiver
   bem definida.

As instruções abaixo implementam o segundo modo. Ao final da seção do
Agendador de Tarefas há a pequena alteração necessária para o modo recomendado.

## 2. Pré-requisitos

- Windows 10/11 ou Windows Server 2019 ou superior, 64 bits;
- conta Windows dedicada, por exemplo `svc_crm_webhook`;
- acesso à internet estável;
- endereço IP fixo ou reserva DHCP para o computador;
- Python compatível com `requires-python = ">=3.11"`;
- `git` e `uv` instalados;
- PostgreSQL local ou uma conexão Neon;
- domínio gerenciado pela Cloudflare para publicar o webhook;
- acesso administrativo apenas durante a instalação e configuração;
- nobreak recomendado.

Configure o Windows Update para não reiniciar a máquina durante o expediente e
desative suspensão/hibernação enquanto o equipamento estiver ligado. O monitor
pode ser desligado sem interromper os processos.

Não execute a instalação de produção dentro de `Downloads`, `Desktop` ou pasta
sincronizada pelo OneDrive. Neste guia será usado:

```text
C:\Apps\CRM_Webhook
```

## 3. Preparar o usuário e a pasta

Crie uma conta Windows dedicada sem privilégios administrativos para executar
a API e o painel. Conceda a ela permissão de leitura e gravação somente na
pasta do projeto e na pasta de logs.

Em PowerShell:

```powershell
New-Item -ItemType Directory -Path C:\Apps -Force
git clone URL_DO_REPOSITORIO C:\Apps\CRM_Webhook
Set-Location C:\Apps\CRM_Webhook
uv sync --frozen
uv run pytest -q
```

O projeto usa `pyproject.toml` e `uv.lock`; não é necessário criar um
`requirements.txt`. Em produção, nunca use `--reload` no Uvicorn.

## 4. Configurar o banco

### Opção A — PostgreSQL no mesmo computador

Esta opção mantém aplicação e dados dentro da empresa. Instale uma versão
suportada do PostgreSQL para Windows e mantenha o serviço do banco com início
automático. Não use o SQLite padrão em produção: FastAPI e Streamlit acessam o
mesmo banco concorrentemente.

No pgAdmin ou `psql`, conectado como administrador, crie um usuário e o banco:

```sql
CREATE ROLE crm_app LOGIN PASSWORD 'SUBSTITUA_POR_UMA_SENHA_FORTE';
CREATE DATABASE crm_webhook OWNER crm_app;
```

Mantenha o PostgreSQL ouvindo apenas em `localhost` se somente este computador
o utiliza. Não abra a porta 5432 no firewall ou no roteador.

### Opção B — Neon PostgreSQL

O FastAPI e o Streamlit continuam locais, mas o banco permanece na nuvem. Use
a URL pooled fornecida pelo Neon. Essa opção simplifica backup e disponibilidade
do banco, mas exige internet para todas as consultas.

### Arquivo `.env`

Crie `C:\Apps\CRM_Webhook\.env` e restrinja sua leitura à conta de serviço e
aos administradores:

```env
DATABASE_URL=postgresql+psycopg://crm_app:SENHA_URL_ENCODED@127.0.0.1:5432/crm_webhook
ENVIRONMENT=production
LOG_LEVEL=INFO
```

Para Neon, substitua a URL pela conexão pooled completa, incluindo os
parâmetros TLS fornecidos pelo serviço.

Este projeto instala Psycopg 3. O esquema correto é
`postgresql+psycopg://`, e não `postgresql+psycopg2://`. Se a senha contiver
`@`, `/`, `:`, `#`, `%` ou outro caractere reservado, aplique URL encoding.
Nunca versione o `.env`; ele já está listado no `.gitignore`.

## 5. Testar manualmente antes de agendar

Abra um PowerShell na raiz do projeto e inicie a API:

```powershell
Set-Location C:\Apps\CRM_Webhook
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Em outro PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

Resposta esperada:

```text
status
------
ok
```

Teste também o painel:

```powershell
Set-Location C:\Apps\CRM_Webhook
.\.venv\Scripts\python.exe -m streamlit run dashboard/app.py `
  --server.address=127.0.0.1 `
  --server.port=8501 `
  --server.headless=true
```

Abra `http://127.0.0.1:8501`. Encerre os dois testes com `Ctrl+C` antes de
criar as tarefas.

## 6. Criar os scripts de execução

Crie as pastas:

```powershell
New-Item -ItemType Directory -Path C:\Apps\CRM_Webhook\ops\windows -Force
New-Item -ItemType Directory -Path C:\Apps\CRM_Webhook\logs -Force
```

### `ops\windows\run-api.ps1`

```powershell
$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\Apps\CRM_Webhook"
$Now = Get-Date

if ($Now.Hour -lt 7 -or $Now.Hour -ge 20) {
    exit 0
}

Set-Location $ProjectRoot
New-Item -ItemType Directory -Path "$ProjectRoot\logs" -Force | Out-Null

& "$ProjectRoot\.venv\Scripts\python.exe" -m uvicorn api.main:app `
    --host 127.0.0.1 `
    --port 8000 `
    --proxy-headers `
    --forwarded-allow-ips=127.0.0.1 `
    1>> "$ProjectRoot\logs\api.log" `
    2>> "$ProjectRoot\logs\api-error.log"

exit $LASTEXITCODE
```

### `ops\windows\run-dashboard.ps1`

Para acesso somente no próprio computador, mantenha
`--server.address=127.0.0.1`:

```powershell
$ErrorActionPreference = "Stop"
$ProjectRoot = "C:\Apps\CRM_Webhook"
$Now = Get-Date

if ($Now.Hour -lt 7 -or $Now.Hour -ge 20) {
    exit 0
}

Set-Location $ProjectRoot
New-Item -ItemType Directory -Path "$ProjectRoot\logs" -Force | Out-Null

& "$ProjectRoot\.venv\Scripts\python.exe" -m streamlit run dashboard/app.py `
    --server.address=127.0.0.1 `
    --server.port=8501 `
    --server.headless=true `
    1>> "$ProjectRoot\logs\dashboard.log" `
    2>> "$ProjectRoot\logs\dashboard-error.log"

exit $LASTEXITCODE
```

Se outras máquinas da rede interna precisarem abrir o painel, altere somente o
dashboard para `--server.address=0.0.0.0` e crie uma regra restrita à sub-rede
corporativa. Exemplo, executado como administrador e com a sub-rede correta:

```powershell
New-NetFirewallRule `
  -DisplayName "CRM Streamlit 8501 - rede interna" `
  -Direction Inbound `
  -Action Allow `
  -Protocol TCP `
  -LocalPort 8501 `
  -RemoteAddress 192.168.1.0/24
```

O painel contém dados pessoais e atualmente não possui autenticação própria.
Não use `Any` em `-RemoteAddress`, não encaminhe a porta 8501 no roteador e não
publique o Streamlit pelo Tunnel sem adicionar uma camada de autenticação.

### `ops\windows\start-tunnel.ps1`

```powershell
$ErrorActionPreference = "Stop"
$Now = Get-Date

if ($Now.Hour -lt 7 -or $Now.Hour -ge 20) {
    exit 0
}

$Service = Get-Service -Name cloudflared
if ($Service.Status -ne "Running") {
    Start-Service -Name cloudflared
}
```

### `ops\windows\stop-stack.ps1`

```powershell
$ErrorActionPreference = "Continue"
$ProjectPython = "C:\Apps\CRM_Webhook\.venv\Scripts\python.exe"

# Encerra somente os processos Python desta instalação. A validação do caminho
# e da linha de comando evita atingir outras aplicações Python do computador.
Get-CimInstance Win32_Process |
    Where-Object {
        $_.ExecutablePath -ieq $ProjectPython -and
        ($_.CommandLine -like "*uvicorn api.main:app*" -or
         $_.CommandLine -like "*streamlit run dashboard/app.py*")
    } |
    ForEach-Object {
        & taskkill.exe /PID $_.ProcessId /T /F | Out-Null
    }

Stop-ScheduledTask -TaskName "CRM Webhook - API"
Stop-ScheduledTask -TaskName "CRM Webhook - Dashboard"
Stop-Service -Name cloudflared -Force
```

Os arquivos de log podem conter erros com dados de negócio. Restrinja o acesso
à pasta `logs` e defina uma política de retenção; não a publique nem a envie ao
Git.

## 7. Publicar o FastAPI com Cloudflare Tunnel

O computador da empresa normalmente está atrás de NAT e não deve receber uma
porta aberta diretamente da internet. Use um Tunnel nomeado e permanente:

1. No Cloudflare Zero Trust, abra **Networking > Tunnels**.
2. Crie um Tunnel chamado `crm-webhook-windows`.
3. Selecione Windows e copie o comando de instalação apresentado.
4. Abra o Prompt de Comando como administrador e execute o comando. Ele terá o
   formato abaixo; use o token real somente no terminal:

```cmd
cloudflared.exe service install TOKEN_DO_TUNNEL
```

5. Em **Routes**, adicione uma **Published application**:

```text
Hostname: api.seudominio.com
Service URL: http://localhost:8000
```

6. Deixe o serviço com início manual, pois o Agendador o ligará às 07:00:

```powershell
Set-Service -Name cloudflared -StartupType Manual
```

7. Configure recuperação automática do serviço, em Prompt de Comando elevado:

```cmd
sc.exe failure cloudflared reset= 86400 actions= restart/5000/restart/15000/restart/60000
```

O token do Tunnel é uma credencial. Não o coloque no repositório, nos scripts
ou no `deploy_local.md`. O `cloudflared` para Windows não se atualiza sozinho;
inclua sua atualização na manutenção periódica.

Não use URL aleatória `trycloudflare.com` em produção.

### Segurança antes de publicar

O estado atual do projeto merece atenção antes de receber dados reais:

- a API ainda não valida `WEBHOOK_SECRET`, HMAC ou Bearer token;
- `GET /webhook/leads` e `GET /webhook/inscricoes` expõem dados pessoais;
- `/docs` e `/openapi.json` ficam públicos;
- o dashboard não possui autenticação própria.

Antes da produção, implemente autenticação do webhook ou uma allowlist dos IPs
oficiais do CRM, aplique rate limiting e bloqueie na borda as rotas de leitura,
Swagger e OpenAPI. Não coloque uma tela de login humana na frente do `POST`
usado pelo CRM, a menos que ele suporte a credencial de serviço correspondente.

## 8. Configurar o Agendador de Tarefas

Abra **Agendador de Tarefas > Biblioteca do Agendador** e use **Criar Tarefa**,
não “Criar Tarefa Básica”. Use os nomes exatamente como aparecem abaixo.

### Tarefa `CRM Webhook - API`

**Geral**

- executar com a conta `svc_crm_webhook`;
- marcar **Executar independentemente de o usuário estar conectado**;
- não é necessário usar privilégios mais altos.

**Disparadores**

- diariamente às `07:00`;
- ao inicializar o computador.

O segundo disparador recupera automaticamente uma reinicialização ocorrida
entre 07:00 e 20:00. O próprio script sai sem iniciar fora dessa janela.

**Ação**

```text
Programa: powershell.exe
Argumentos: -NoProfile -ExecutionPolicy Bypass -File "C:\Apps\CRM_Webhook\ops\windows\run-api.ps1"
Iniciar em: C:\Apps\CRM_Webhook
```

**Condições e configurações**

- desmarcar “Iniciar a tarefa somente se o computador estiver usando energia
  elétrica”, se houver nobreak e a política da empresa permitir;
- marcar **Ativar o computador para executar esta tarefa**;
- marcar **Executar a tarefa assim que possível após um início agendado ser
  perdido**;
- se a tarefa falhar, reiniciar a cada 5 minutos, por pelo menos 3 tentativas;
- se já estiver em execução, escolher **Não iniciar uma nova instância**.

### Tarefa `CRM Webhook - Dashboard`

Repita a configuração anterior e altere apenas a ação:

```text
Programa: powershell.exe
Argumentos: -NoProfile -ExecutionPolicy Bypass -File "C:\Apps\CRM_Webhook\ops\windows\run-dashboard.ps1"
Iniciar em: C:\Apps\CRM_Webhook
```

### Tarefa `CRM Webhook - Tunnel`

Esta tarefa precisa executar com privilégios elevados para iniciar o serviço.

**Disparadores**

- diariamente às `07:00`;
- ao inicializar o computador.

**Ação**

```text
Programa: powershell.exe
Argumentos: -NoProfile -ExecutionPolicy Bypass -File "C:\Apps\CRM_Webhook\ops\windows\start-tunnel.ps1"
Iniciar em: C:\Apps\CRM_Webhook
```

Marque **Executar com privilégios mais altos**, **Executar assim que possível**
e **Não iniciar uma nova instância**.

### Tarefa `CRM Webhook - Encerrar`

Execute esta tarefa como `SYSTEM` ou com uma conta administrativa, com
privilégios mais altos.

**Disparador**

- diariamente às `20:00`.

**Ação**

```text
Programa: powershell.exe
Argumentos: -NoProfile -ExecutionPolicy Bypass -File "C:\Apps\CRM_Webhook\ops\windows\stop-stack.ps1"
Iniciar em: C:\Apps\CRM_Webhook
```

Marque **Executar assim que possível após um início agendado ser perdido**.
Como proteção adicional, configure as tarefas da API e do dashboard para serem
interrompidas após 13 horas.

### Modo recomendado: API 24 horas

Para manter o recebimento de webhooks 24×7:

- remova a verificação de horário de `run-api.ps1`;
- deixe o serviço `cloudflared` com início automático;
- remova `Stop-Service cloudflared` de `stop-stack.ps1`;
- remova `Stop-ScheduledTask` da API de `stop-stack.ps1`;
- mantenha somente o dashboard agendado das 07:00 às 20:00.

```powershell
Set-Service -Name cloudflared -StartupType Automatic
```

## 9. Validar as tarefas

No Agendador, clique com o botão direito e selecione **Executar** nesta ordem:

1. `CRM Webhook - API`;
2. `CRM Webhook - Dashboard`;
3. `CRM Webhook - Tunnel`.

Confirme:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Get-Service cloudflared
Get-NetTCPConnection -State Listen -LocalPort 8000,8501
Get-Content C:\Apps\CRM_Webhook\logs\api-error.log -Tail 50
Get-Content C:\Apps\CRM_Webhook\logs\dashboard-error.log -Tail 50
```

Teste o endpoint público:

```powershell
Invoke-RestMethod https://api.seudominio.com/health
```

Depois envie um Lead fictício:

```powershell
$Headers = @{
    "Content-Type" = "application/json"
    "X-Event-Id" = "deploy-local-lead-001"
}

$Body = @{
    leadid = "deploy-local-lead-001"
    fullname = "Lead de validacao"
    createdon = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json

Invoke-RestMethod `
  -Method Post `
  -Uri https://api.seudominio.com/webhook `
  -Headers $Headers `
  -Body $Body
```

Verifique o Lead no painel em até 10 segundos. Reenvie o mesmo evento e
confirme `duplicate = true`.

Por fim, execute manualmente `CRM Webhook - Encerrar` e confirme que as portas
8000 e 8501 não estão mais ouvindo e que o serviço `cloudflared` está parado:

```powershell
Get-NetTCPConnection -State Listen -LocalPort 8000,8501 -ErrorAction SilentlyContinue
Get-Service cloudflared
```

## 10. Acesso ao dashboard

Com `--server.address=127.0.0.1`, o endereço é:

```text
http://127.0.0.1:8501
```

Se o painel estiver liberado para a rede interna, descubra o IPv4 do computador:

```powershell
Get-NetIPAddress -AddressFamily IPv4 |
  Where-Object { $_.IPAddress -notlike "127.*" }
```

O endereço será semelhante a:

```text
http://192.168.1.50:8501
```

Use reserva DHCP para evitar que esse endereço mude.

## 11. Backup e recuperação

Para PostgreSQL local, mantenha backup automático em outro equipamento ou
armazenamento corporativo. Um backup que permanece somente no mesmo disco não
protege contra falha do computador.

Exemplo de backup manual em formato customizado:

```powershell
& "C:\Program Files\PostgreSQL\VERSAO\bin\pg_dump.exe" `
  --host=127.0.0.1 `
  --username=crm_app `
  --format=custom `
  --file="D:\Backups\crm_webhook.backup" `
  crm_webhook
```

Agende o backup após as 20:00, proteja a senha com o mecanismo apropriado do
PostgreSQL/Windows e teste a restauração periodicamente. Defina também retenção
e rotação para `logs\*.log`.

## 12. Atualização da aplicação

Faça a atualização fora do horário de operação:

```powershell
Set-Location C:\Apps\CRM_Webhook
git status --short
git pull --ff-only
uv sync --frozen
uv run pytest -q
```

Não use `git reset --hard` para atualizar. Se houver migration de banco no
futuro, faça backup antes e execute o procedimento de migration documentado.
O projeto atualmente usa `create_all()`: ele cria tabelas ausentes, mas não
altera corretamente tabelas existentes quando o schema muda.

Depois da atualização, execute as tarefas manualmente e repita o health check e
o teste ponta a ponta.

## 13. Operação diária

Monitore pelo menos:

- histórico das quatro tarefas no Agendador;
- estado do serviço `cloudflared`;
- disponibilidade local e pública de `/health`;
- logs `api-error.log` e `dashboard-error.log`;
- eventos com status de erro;
- tempo desde o último webhook;
- espaço em disco e execução dos backups;
- serviço do PostgreSQL, quando local;
- relógio e fuso do Windows (`America/Sao_Paulo`/Horário de Brasília).

A aplicação remove na inicialização os registros fora do dia corrente de
`America/Sao_Paulo`. Isso é comportamento atual do projeto e deve ser aceito
explicitamente antes da produção.

## 14. Problemas comuns

### A tarefa inicia e encerra imediatamente

Confira se o teste está sendo feito entre 07:00 e 20:00 e consulte os arquivos
em `logs`. Confirme também que a conta da tarefa tem acesso ao projeto, ao
`.env` e ao executável em `.venv\Scripts\python.exe`.

### O painel abre apenas no computador servidor

Para acesso pela rede, use `--server.address=0.0.0.0`, crie a regra de firewall
restrita à sub-rede e acesse pelo IPv4 fixo do computador.

### Cloudflare retorna `502 Bad Gateway`

Teste primeiro:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Get-Service cloudflared
```

Se o health local falhar, investigue a API. Se funcionar localmente, revise a
Published application do Tunnel e o log do `cloudflared`.

### `No module named psycopg2`

Troque o esquema da URL para `postgresql+psycopg://`. O projeto usa Psycopg 3.

### O computador reiniciou e nada iniciou

Confirme os disparadores “ao inicializar”, a opção “Executar assim que possível”
e as credenciais salvas da conta de serviço. Verifique se o horário atual está
entre 07:00 e 20:00.

### Eventos fora do horário não aparecem

Esse é o resultado esperado quando API e Tunnel são desligados. Verifique as
retentativas do CRM ou adote o modo recomendado com a API 24×7.

## 15. Checklist final

- [ ] projeto instalado fora de pasta sincronizada;
- [ ] `uv sync --frozen` e testes concluídos;
- [ ] PostgreSQL configurado; SQLite não usado em produção;
- [ ] `.env` protegido e fora do Git;
- [ ] URL usa `postgresql+psycopg://`;
- [ ] API escuta somente em `127.0.0.1:8000`;
- [ ] acesso ao Streamlit limitado ao computador ou à sub-rede corporativa;
- [ ] Tunnel nomeado configurado para `http://localhost:8000`;
- [ ] segredo/HMAC ou allowlist do CRM implementado;
- [ ] endpoints de leitura, Swagger e OpenAPI protegidos;
- [ ] tarefas de 07:00, inicialização e 20:00 testadas;
- [ ] comportamento fora do horário aprovado pelo negócio;
- [ ] backup externo e restauração testados;
- [ ] logs, espaço em disco, energia e reinicializações monitorados;
- [ ] teste de Lead, inscrição e duplicidade concluído.

## Referências oficiais

- [Instalador do PostgreSQL para Windows](https://www.postgresql.org/download/windows/)
- [Criar e publicar um Cloudflare Tunnel](https://developers.cloudflare.com/tunnel/get-started/)
- [Executar cloudflared como serviço no Windows](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/as-a-service/windows/)
- [Download e atualização do cloudflared](https://developers.cloudflare.com/tunnel/downloads/)
- [Agendador de Tarefas do Windows](https://learn.microsoft.com/windows-server/administration/windows-commands/schtasks)
