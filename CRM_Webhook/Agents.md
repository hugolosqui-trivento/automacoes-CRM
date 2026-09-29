# AGENTS.md

## 1. Objetivo do projeto

Este projeto implementa uma arquitetura para recebimento e acompanhamento quase em tempo real de Leads do CRM Educacional.

A solução deve separar claramente duas responsabilidades:

- **FastAPI**: recebe os webhooks enviados pelo CRM, valida os dados, registra os eventos e persiste os Leads.
- **Streamlit**: apresenta um painel operacional para acompanhamento dos Leads, usando atualização periódica nativa com `st.fragment(run_every=...)`.

Arquitetura esperada:

```text
CRM Educacional
      |
      | POST /webhook
      v
   FastAPI
      |
      | valida / normaliza
      v
 PostgreSQL / Neon
      |
      | consulta
      v
  Streamlit
      |
      | st.fragment(run_every="5s")
      v
Painel quase em tempo real
```

O Streamlit **não deve ser responsável por receber o webhook**.

O FastAPI deve ser o ponto de entrada público para integrações externas.

---

## 2. Princípios de arquitetura

Todo desenvolvimento deve seguir estes princípios:

1. FastAPI e Streamlit devem ser aplicações independentes.
2. Ambos podem compartilhar módulos Python comuns.
3. O banco de dados é o ponto de integração entre FastAPI e Streamlit.
4. O Streamlit não deve depender de chamadas diretas ao FastAPI para montar o dashboard quando os dados já estiverem persistidos.
5. O FastAPI deve responder rapidamente aos webhooks.
6. Processamentos pesados não devem bloquear a resposta do webhook.
7. Credenciais nunca devem ser inseridas diretamente no código.
8. Toda configuração sensível deve usar variáveis de ambiente ou `st.secrets`.
9. O código deve estar preparado para PostgreSQL, preferencialmente Neon.
10. O dashboard deve evitar reruns completos desnecessários.
11. Para atualização periódica no Streamlit, priorizar `st.fragment(run_every=...)`.
12. O código deve ser simples, modular e legível.

---

## 3. Estrutura recomendada do projeto

```text
projeto/
|
|-- AGENTS.md
|-- README.md
|-- requirements.txt
|-- .env.example
|-- .gitignore
|
|-- api/
|   |-- __init__.py
|   |-- main.py
|   |-- routes/
|   |   `-- webhook.py
|   |-- schemas/
|   |   `-- lead.py
|   `-- services/
|       `-- lead_service.py
|
|-- dashboard/
|   |-- app.py
|   `-- components/
|       |-- metrics.py
|       `-- leads_table.py
|
|-- database/
|   |-- connection.py
|   |-- models.py
|   `-- repositories/
|       `-- leads.py
|
|-- shared/
|   |-- config.py
|   |-- logging.py
|   `-- utils.py
|
`-- tests/
    |-- test_webhook.py
    `-- test_leads_repository.py
```

A estrutura pode ser simplificada durante o protótipo, mas as responsabilidades devem permanecer separadas.

---

## 4. Dependências principais

Exemplo de `requirements.txt`:

```txt
fastapi
uvicorn[standard]
streamlit
sqlalchemy
psycopg2-binary
pydantic
pydantic-settings
python-dotenv
pandas
httpx
```

Opcionalmente:

```txt
alembic
pytest
```

Usar Alembic quando houver necessidade de controlar migrations do banco.

---

## 5. Variáveis de ambiente

Nunca armazenar credenciais reais no repositório.

Exemplo de `.env.example`:

```env
DATABASE_URL=postgresql+psycopg2://usuario:senha@host/banco?sslmode=require
WEBHOOK_SECRET=alterar_em_producao
ENVIRONMENT=development
LOG_LEVEL=INFO
```

No Streamlit Community Cloud, preferir:

```toml
# .streamlit/secrets.toml
DATABASE_URL = "..."
```

O arquivo real `secrets.toml` não deve ser versionado.

---

## 6. Configuração compartilhada

Centralizar leitura das configurações.

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    webhook_secret: str | None = None
    environment: str = "development"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"

settings = Settings()
```

Evitar chamadas espalhadas diretamente a `os.getenv()` quando uma configuração compartilhada puder ser usada.

---

# FASTAPI

## 7. Responsabilidade do FastAPI

O FastAPI deve:

- receber webhooks do CRM;
- validar o payload;
- rejeitar payloads inválidos;
- autenticar a origem quando possível;
- evitar duplicação de eventos;
- registrar data/hora de recebimento;
- persistir os dados;
- responder rapidamente;
- disponibilizar endpoint de saúde.

O FastAPI não deve:

- renderizar dashboards;
- executar consultas analíticas pesadas durante o recebimento;
- aguardar processamento desnecessário antes de responder ao CRM;
- manter estado crítico apenas em memória.

---

## 8. Aplicação FastAPI mínima

```python
from fastapi import FastAPI

app = FastAPI(
    title="CRM Webhook API",
    version="1.0.0",
)

@app.get("/health")
def health():
    return {"status": "ok"}
```

Executar localmente:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

Produção:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 9. Endpoint principal

O endpoint padrão será:

```text
POST /webhook
```

Exemplo:

```python
from fastapi import APIRouter, HTTPException, Request

router = APIRouter()

@router.post("/webhook")
async def webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Payload JSON inválido",
        )

    # validar
    # normalizar
    # persistir

    return {"status": "received"}
```

---

## 10. Schemas Pydantic

Sempre que o contrato do CRM for conhecido, usar Pydantic.

```python
from datetime import datetime
from pydantic import BaseModel, EmailStr

class LeadWebhook(BaseModel):
    id: str
    nome: str | None = None
    email: EmailStr | None = None
    telefone: str | None = None
    unidade: str | None = None
    origem: str | None = None
    created_at: datetime | None = None
```

Se o CRM enviar estruturas diferentes para Leads, inscrições ou outros eventos, criar schemas separados.

---

## 11. Envelope de evento recomendado

Sempre que possível, normalizar os eventos para uma estrutura interna:

```json
{
  "event_id": "abc123",
  "event_type": "lead.created",
  "source": "crm_educacional",
  "received_at": "2026-09-25T14:00:00Z",
  "data": {}
}
```

Isso facilita adicionar futuramente:

- inscrição criada;
- inscrição alterada;
- matrícula;
- atendimento;
- mudança de etapa;
- pagamento.

---

## 12. Idempotência

Webhooks podem ser reenviados.

O projeto deve evitar duplicação.

Prioridade:

1. usar um identificador único enviado pelo CRM;
2. armazenar `event_id`;
3. criar índice `UNIQUE`;
4. ignorar eventos repetidos de forma segura.

Exemplo conceitual:

```sql
CREATE UNIQUE INDEX ux_webhook_event_id
ON webhook_events(event_id);
```

Se o CRM não fornecer um identificador único, gerar uma chave baseada em campos estáveis do evento.

---

## 13. Resposta do webhook

Sempre que o evento for recebido corretamente:

```http
HTTP/1.1 200 OK
```

ou:

```http
HTTP/1.1 202 Accepted
```

Resposta sugerida:

```json
{
  "status": "received"
}
```

Evitar retornar grandes volumes de dados.

---

## 14. Status HTTP recomendados

```text
200 / 202 -> evento aceito
400       -> payload malformado
401       -> autenticação ausente ou inválida
403       -> origem não autorizada
409       -> conflito relevante
422       -> erro de validação
500       -> erro inesperado interno
```

Não retornar `200` quando o evento não puder ser processado de forma válida.

---

## 15. Segurança do webhook

Se o CRM permitir, usar uma destas estratégias:

### Header secreto

```http
X-Webhook-Secret: segredo
```

Exemplo:

```python
from fastapi import Header, HTTPException

async def validate_secret(
    x_webhook_secret: str | None = Header(default=None)
):
    if x_webhook_secret != settings.webhook_secret:
        raise HTTPException(
            status_code=401,
            detail="Webhook não autorizado",
        )
```

Melhor ainda, se o CRM suportar:

- assinatura HMAC;
- token Bearer;
- assinatura criptográfica do payload.

Nunca confiar apenas no fato de a URL não ser conhecida.

---

## 16. Persistência antes da análise

O evento recebido deve ser persistido antes de qualquer transformação complexa.

```text
Webhook recebido
      |
      v
salvar payload bruto
      |
      v
normalizar campos principais
      |
      v
atualizar tabela de leads
```

Manter o payload bruto ajuda na auditoria e no diagnóstico de mudanças do CRM.

---

## 17. Modelo de tabela de eventos

```sql
CREATE TABLE webhook_events (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT UNIQUE,
    event_type TEXT,
    source TEXT,
    payload JSONB NOT NULL,
    received_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ,
    status TEXT DEFAULT 'received'
);
```

---

## 18. Modelo de tabela de Leads

```sql
CREATE TABLE leads (
    lead_id TEXT PRIMARY KEY,
    nome TEXT,
    email TEXT,
    telefone TEXT,
    unidade TEXT,
    origem TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    received_at TIMESTAMPTZ DEFAULT NOW()
);
```

Os nomes devem ser adaptados aos campos reais do CRM Educacional.

---

## 19. Upsert de Leads

O webhook pode receber atualizações de Leads já existentes.

Usar `UPSERT` em vez de inserir duplicados.

```sql
INSERT INTO leads (...)
VALUES (...)
ON CONFLICT (lead_id)
DO UPDATE SET
    nome = EXCLUDED.nome,
    email = EXCLUDED.email,
    unidade = EXCLUDED.unidade,
    updated_at = NOW();
```

---

## 20. Não bloquear o webhook

Evitar:

```python
@router.post("/webhook")
async def webhook(...):
    executar_relatorio()
    consultar_varias_apis()
    gerar_graficos()
    enviar_email()
```

Preferir:

```text
receber
  ->
validar
  ->
persistir
  ->
responder
```

---

## 21. Logs

Registrar pelo menos:

- horário;
- endpoint;
- tipo de evento;
- identificador do evento;
- identificador do Lead;
- status de processamento;
- erro, se houver.

Nunca registrar:

- senhas;
- tokens;
- secrets;
- credenciais de banco.

Evitar registrar dados pessoais completos sem necessidade.

---

## 22. Health check

Obrigatório:

```text
GET /health
```

Resposta:

```json
{
  "status": "ok"
}
```

Opcionalmente verificar conexão com banco.

---

# BANCO DE DADOS

## 23. Banco recomendado

Preferência:

```text
PostgreSQL
```

Para protótipo ou produção de pequeno/médio porte:

```text
Neon PostgreSQL
```

Tanto FastAPI quanto Streamlit devem acessar o mesmo banco.

---

## 24. SQLAlchemy

Centralizar o engine.

```python
from sqlalchemy import create_engine

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)
```

Evitar criar um novo engine a cada requisição.

---

## 25. Repositories

Consultas SQL devem ficar preferencialmente em uma camada de repositório.

Exemplo:

```python
def buscar_leads_recentes(conn, limite=20):
    ...
```

O dashboard não deve acumular SQL complexo diretamente em vários arquivos.

---

# STREAMLIT

## 26. Responsabilidade do Streamlit

O Streamlit deve:

- apresentar os Leads recebidos;
- consultar dados persistidos;
- mostrar métricas operacionais;
- atualizar blocos específicos automaticamente;
- permitir filtros de visualização.

O Streamlit não deve:

- atuar como receptor principal de webhook;
- armazenar o estado oficial dos eventos;
- substituir o banco;
- executar polling agressivo sem necessidade.

---

## 27. Atualização nativa com `st.fragment`

A solução padrão para atualização periódica será:

```python
@st.fragment(run_every="5s")
def painel_tempo_real():
    ...
```

Exemplo:

```python
import streamlit as st
import pandas as pd

@st.fragment(run_every="5s")
def painel_tempo_real():

    query = """
        SELECT
            lead_id,
            nome,
            email,
            unidade,
            origem,
            created_at,
            received_at
        FROM leads
        ORDER BY received_at DESC
        LIMIT 50
    """

    df = pd.read_sql(query, engine)

    st.subheader("Leads recentes")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

painel_tempo_real()
```

---

## 28. Frequência de atualização

Valor inicial recomendado:

```python
run_every="5s"
```

Outras opções:

```python
run_every="10s"
run_every="30s"
run_every="1m"
```

Para monitoramento operacional de Leads, priorizar inicialmente:

```text
5 a 10 segundos
```

Evitar atualização a cada segundo sem necessidade operacional comprovada.

---

## 29. Fragmentos independentes

Não colocar todo o dashboard em um único fragmento.

```python
st.title("Monitoramento CRM")

mostrar_graficos_historicos()

@st.fragment(run_every="5s")
def indicadores_recentes():
    ...

@st.fragment(run_every="10s")
def tabela_leads():
    ...

indicadores_recentes()
tabela_leads()
```

Dessa forma, áreas históricas permanecem estáticas enquanto dados operacionais são atualizados.

---

## 30. Métricas recomendadas

O painel deve priorizar:

```text
Leads hoje
Leads na última hora
Leads nos últimos 5 minutos
Último Lead recebido
Horário do último webhook
Leads por unidade hoje
Leads por origem hoje
```

Evitar transformar o Streamlit em uma simples cópia do Power BI.

O foco é acompanhamento operacional.

---

## 31. Tabela de Leads recentes

Mostrar inicialmente:

```text
Horário
Nome
Unidade
Origem
Curso
Forma de ingresso
Status
```

Quantidade sugerida:

```text
20 a 100 registros
```

Evitar carregar milhares de linhas em atualização de 5 segundos.

---

## 32. Cache

Conexões podem usar:

```python
@st.cache_resource
def get_engine():
    ...
```

Exemplo:

```python
@st.cache_resource
def get_engine():
    return create_engine(
        st.secrets["DATABASE_URL"],
        pool_pre_ping=True,
    )
```

Não aplicar `st.cache_data` com TTL longo em consultas que precisam representar eventos recentes.

---

## 33. Exemplo de dashboard

```python
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(
    page_title="CRM - Leads em tempo real",
    layout="wide",
)

@st.cache_resource
def get_engine():
    return create_engine(
        st.secrets["DATABASE_URL"],
        pool_pre_ping=True,
    )

engine = get_engine()

def carregar_metricas():
    query = text("""
        SELECT
            COUNT(*) FILTER (
                WHERE received_at >= CURRENT_DATE
            ) AS leads_hoje,

            COUNT(*) FILTER (
                WHERE received_at >= NOW() - INTERVAL '1 hour'
            ) AS leads_ultima_hora,

            COUNT(*) FILTER (
                WHERE received_at >= NOW() - INTERVAL '5 minutes'
            ) AS leads_5_min

        FROM leads
    """)

    with engine.connect() as conn:
        return pd.read_sql(query, conn).iloc[0]

def carregar_leads_recentes():
    query = text("""
        SELECT
            nome,
            unidade,
            origem,
            received_at
        FROM leads
        ORDER BY received_at DESC
        LIMIT 30
    """)

    with engine.connect() as conn:
        return pd.read_sql(query, conn)

st.title("Monitoramento de Leads")

@st.fragment(run_every="5s")
def painel_tempo_real():

    metricas = carregar_metricas()

    c1, c2, c3 = st.columns(3)

    c1.metric("Leads hoje", int(metricas["leads_hoje"]))
    c2.metric("Última hora", int(metricas["leads_ultima_hora"]))
    c3.metric("Últimos 5 minutos", int(metricas["leads_5_min"]))

    st.subheader("Leads recentes")

    df = carregar_leads_recentes()

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

painel_tempo_real()
```

---

# INTEGRAÇÃO FASTAPI + STREAMLIT

## 34. Comunicação entre componentes

Fluxo recomendado:

```text
FastAPI -> PostgreSQL <- Streamlit
```

Evitar como arquitetura principal:

```text
Streamlit -> FastAPI -> PostgreSQL
```

O dashboard pode consumir endpoints do FastAPI quando existir uma razão específica, mas para o painel operacional interno o acesso direto ao banco tende a ser mais simples.

---

## 35. Consistência de tempo

Armazenar timestamps no banco com timezone:

```text
TIMESTAMPTZ
```

Preferencialmente armazenar em UTC.

A apresentação no Streamlit pode converter para:

```text
America/Sao_Paulo
```

Não armazenar datas críticas como texto.

---

# DESENVOLVIMENTO

## 36. Execução local

Terminal 1:

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2:

```bash
streamlit run dashboard/app.py
```

URLs locais:

```text
FastAPI:
http://localhost:8000

Swagger:
http://localhost:8000/docs

Streamlit:
http://localhost:8501
```

---

## 37. Teste manual do webhook

```bash
curl -X POST \
  http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "id": "lead-001",
    "nome": "Lead Teste",
    "email": "teste@example.com",
    "unidade": "Lorena",
    "origem": "Organico"
  }'
```

Resposta esperada:

```json
{
  "status": "received"
}
```

Depois verificar se o Lead aparece no Streamlit no próximo ciclo do fragmento.

---

## 38. Swagger

Durante desenvolvimento, usar:

```text
http://localhost:8000/docs
```

para testar endpoints.

Não assumir que `/docs` deve necessariamente permanecer público em produção.

---

# TUNNEL E DESENVOLVIMENTO

## 39. Cloudflare Tunnel

Durante testes locais ou Codespaces, o FastAPI pode ser exposto com Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://localhost:8000
```

Fluxo:

```text
CRM
 |
 v
URL Cloudflare
 |
 v
localhost:8000
 |
 v
FastAPI
```

Cloudflare Tunnel não substitui o FastAPI.

Ele apenas encaminha requisições externas para o servidor.

---

## 40. Codespaces

Codespaces pode ser utilizado para:

- desenvolvimento;
- testes;
- execução temporária;
- validação do webhook.

Não tratar Codespaces como infraestrutura de produção permanente para receber webhooks críticos.

---

# DEPLOY

## 41. Streamlit

O dashboard pode permanecer no:

```text
Streamlit Community Cloud
```

O deploy deve apontar para:

```text
dashboard/app.py
```

Configurar `DATABASE_URL` em Secrets.

---

## 42. FastAPI

O FastAPI deve ser hospedado em uma plataforma que ofereça:

- execução contínua;
- HTTPS;
- URL pública estável;
- variáveis de ambiente;
- logs;
- restart automático.

Exemplos possíveis:

```text
Render
Railway
Google Cloud Run
Azure App Service
AWS
Fly.io
VPS
```

A escolha da plataforma não deve alterar a arquitetura interna da aplicação.

---

## 43. Arquitetura de produção desejada

```text
                CRM Educacional
                       |
                       | POST
                       v
               FastAPI público
                       |
                       v
                 PostgreSQL
                       ^
                       |
                       |
             Streamlit Community
                    Cloud
```

Neste cenário:

- Codespaces é apenas ambiente de desenvolvimento;
- Cloudflare Tunnel não é obrigatório em produção;
- Streamlit continua sendo o dashboard;
- FastAPI mantém o endpoint público de webhook.

---

# TESTES

## 44. Testes obrigatórios do webhook

Cobrir pelo menos:

```text
payload válido
payload inválido
evento duplicado
falha de banco
secret inválido
campo opcional ausente
```

---

## 45. Teste FastAPI

```python
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

---

# OBSERVABILIDADE

## 46. Campos de auditoria

Sempre que possível armazenar:

```text
received_at
processed_at
event_id
event_type
status
error_message
```

Isso permite identificar:

- último webhook;
- atraso no processamento;
- eventos com erro;
- duplicações;
- períodos sem eventos.

---

## 47. Monitoramento no Streamlit

O dashboard pode mostrar:

```text
Último webhook recebido
Quantidade recebida hoje
Quantidade recebida na última hora
Eventos com erro
Tempo desde o último evento
```

Isso ajuda a detectar falhas na integração.

---

# SEGURANÇA E PRIVACIDADE

## 48. Dados pessoais

Leads podem conter dados pessoais.

Evitar:

- imprimir payloads completos em logs;
- expor e-mail ou telefone em logs públicos;
- armazenar secrets no Git;
- disponibilizar dashboard sem autenticação quando houver dados pessoais.

Aplicar princípio de menor privilégio.

---

## 49. Secrets

Adicionar ao `.gitignore`:

```gitignore
.env
.streamlit/secrets.toml
__pycache__/
*.pyc
```

Nunca commitar:

```text
DATABASE_URL real
senhas
tokens
API keys
WEBHOOK_SECRET
```

---

# PERFORMANCE

## 50. Consultas do Streamlit

Consultas executadas a cada 5 segundos devem ser pequenas.

Preferir:

```sql
ORDER BY received_at DESC
LIMIT 50
```

em vez de:

```sql
SELECT * FROM leads
```

---

## 51. Índices recomendados

```sql
CREATE INDEX idx_leads_received_at
ON leads(received_at DESC);
```

Outros candidatos:

```text
unidade
origem
created_at
event_type
status
```

Não adicionar índices sem necessidade.

---

## 52. Escalabilidade

A primeira versão pode utilizar:

```text
FastAPI
PostgreSQL
Streamlit
```

Não adicionar inicialmente:

```text
Kafka
RabbitMQ
Redis Streams
Celery
Airflow
```

sem uma necessidade comprovada.

Esses componentes podem ser considerados posteriormente se o volume ou complexidade aumentarem.

---

# REGRAS PARA AGENTES DE IA

## 53. Antes de modificar código

Todo agente deve:

1. identificar se a mudança pertence ao FastAPI, Streamlit, banco ou código compartilhado;
2. preservar a separação de responsabilidades;
3. verificar impactos no contrato do webhook;
4. não alterar schemas existentes silenciosamente;
5. não introduzir novas dependências sem justificativa;
6. preservar compatibilidade com PostgreSQL;
7. manter secrets fora do código;
8. executar ou propor testes correspondentes.

---

## 54. Ao alterar o FastAPI

Sempre verificar:

```text
O endpoint continua rápido?
A resposta HTTP continua correta?
Existe risco de duplicação?
Existe validação?
O erro está registrado?
O payload bruto continua auditável?
```

---

## 55. Ao alterar o Streamlit

Sempre verificar:

```text
O rerun é realmente necessário?
A parte dinâmica pode ser um st.fragment?
A consulta está limitada?
Existe cache correto para a conexão?
A atualização periódica está entre 5 e 10 segundos por padrão?
```

Evitar `time.sleep()` para implementar atualização do dashboard.

Não criar loops infinitos como:

```python
while True:
    ...
```

para simular tempo real.

Usar:

```python
@st.fragment(run_every="5s")
```

---

## 56. Ao alterar banco

Não apagar ou renomear colunas em produção sem migration.

Mudanças devem preservar:

```text
event_id
received_at
payload bruto
lead_id
```

quando esses campos já estiverem sendo utilizados.

---

# CRITÉRIOS DE ACEITE

## 57. Webhook

A integração será considerada funcional quando:

- o CRM conseguir realizar `POST`;
- FastAPI retornar sucesso;
- o evento for salvo;
- duplicados não criarem registros inconsistentes;
- erros forem registrados;
- `/health` estiver disponível.

---

## 58. Dashboard

O acompanhamento será considerado funcional quando:

- o Streamlit carregar normalmente;
- o painel consultar o mesmo PostgreSQL;
- novos Leads aparecerem automaticamente;
- não for necessário atualizar manualmente o navegador;
- apenas os fragmentos dinâmicos forem atualizados;
- a atualização ocorrer em aproximadamente 5 a 10 segundos;
- consultas permanecerem leves.

---

## 59. Fluxo de teste ponta a ponta

```text
1. Iniciar FastAPI
2. Iniciar Streamlit
3. Enviar POST de teste
4. Confirmar HTTP 200/202
5. Confirmar inserção no PostgreSQL
6. Aguardar próximo ciclo do st.fragment
7. Confirmar aparecimento do Lead no dashboard
8. Reenviar o mesmo evento
9. Confirmar comportamento idempotente
```

---

# DECISÕES DE PROJETO

## 60. Decisões atuais

```text
Backend de integração: FastAPI
Dashboard operacional: Streamlit
Banco: PostgreSQL
Banco sugerido: Neon
Atualização do dashboard: st.fragment(run_every=...)
Intervalo inicial: 5 segundos
Endpoint principal: POST /webhook
Health check: GET /health
Formato preferencial: JSON
Ambiente de desenvolvimento: local ou GitHub Codespaces
Tunnel de desenvolvimento: Cloudflare Tunnel
Streamlit em produção: Streamlit Community Cloud
FastAPI em produção: serviço HTTP dedicado
```

---

## 61. Evolução futura

Somente adicionar novas camadas quando houver necessidade real.

Possíveis evoluções:

```text
fila assíncrona
worker
Redis
Celery
mensageria
alertas
websocket
Server-Sent Events
observabilidade externa
autenticação do dashboard
Power BI consumindo a mesma camada de dados
```

A solução inicial deve continuar simples.

---

## 62. Regra principal

A regra arquitetural mais importante é:

```text
FastAPI recebe.
PostgreSQL persiste.
Streamlit observa.
```

A comunicação principal deve permanecer desacoplada.

Isso garante que uma falha, reinicialização ou atualização do Streamlit não impeça o CRM de enviar novos Leads.
