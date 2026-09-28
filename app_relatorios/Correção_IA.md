# Integração da correção de redações por IA

## Escopo

Este documento descreve de onde vêm as redações no CRM, como a consulta é feita e quais dados são necessários para reaproveitar a correção por IA em outro sistema.

> **Aviso sobre as saídas:** o formato, os nomes dos campos e o destino das saídas da correção poderão ser alterados. Por esse motivo, as saídas atuais, a planilha de exportação e sua persistência não fazem parte desta documentação e não devem ser tratados como contrato de integração.

Embora a tela que inicia o processo esteja em `pages/5_Corrigir_redações.py`, a consulta e a correção estão implementadas principalmente em:

- `data_loader.py`: aplica cache e inicia o carregamento;
- `services/redacoes.py`: define os campos consultados, prepara as redações e chama a IA;
- `services/crm_api.py`: autentica e consulta a API do CRM Educacional;
- `settings.py`: lê as credenciais e demais configurações.

## Visão geral do fluxo

1. A página chama `carregar_redacoes(settings.crm)`.
2. `carregar_redacoes` chama `buscar_redacoes_entregues` e mantém o resultado em cache por 900 segundos (15 minutos). Na tela atual, o cache dessa consulta é limpo antes de uma busca iniciada pelo botão.
3. `buscar_redacoes_entregues` consulta a entidade `cad_redacao` no CRM.
4. A consulta traz os registros paginados e o código local mantém apenas aqueles cuja situação é `Entregue`.
5. Para cada registro, o tema e o texto da redação são enviados à API do OpenRouter.

## Configuração

As configurações podem vir de variáveis de ambiente ou dos secrets do Streamlit. Quando uma variável de ambiente existe, ela tem precedência.

### CRM

| Configuração | Obrigatória | Uso |
|---|---:|---|
| `CRM_BASE_URL` | Não | URL base do CRM. O padrão atual é `https://trivento.api.crmeducacional.com`. |
| `CRM_USERNAME` | Sim | Usuário usado para obter o token. |
| `CRM_PASSWORD` | Sim | Senha usada para obter o token. |
| `CRM_AUTH_TYPE` | Não | Tipo de autenticação. O padrão é `APICRMEducacional`. |

### IA

| Configuração | Obrigatória | Uso |
|---|---:|---|
| `OPENROUTER_KEY` ou `OPENROUTER_API` | Sim | Chave enviada como Bearer token ao OpenRouter. `OPENROUTER_KEY` tem precedência. |
| `OPENROUTER_MODEL` | Não | Modelo de linguagem. O padrão atual é `openai/gpt-4o-mini`. |

Credenciais e chaves nunca devem ser gravadas no código-fonte, em logs ou na documentação do sistema integrador.

## Autenticação no CRM

A autenticação usa o fluxo de senha exposto pelo CRM:

- método: `POST`;
- endpoint: `{CRM_BASE_URL}/api/token`;
- `Content-Type`: `application/x-www-form-urlencoded`;
- corpo:

```text
grant_type=password
username={CRM_USERNAME}
password={CRM_PASSWORD}
authentication_type={CRM_AUTH_TYPE}
```

O campo `access_token` do JSON retornado é usado nas consultas seguintes como `Authorization: Bearer {access_token}`.

## Consulta das redações no CRM

A origem é a entidade lógica `cad_redacao`, consultada pelo endpoint de Localização Avançada:

- método: `POST`;
- endpoint: `{CRM_BASE_URL}/api/LocalizacaoAvancada`;
- `Authorization`: `Bearer {access_token}`;
- `Content-Type`: `application/xml`;
- cabeçalho `Pagina`: começa em `1` e é incrementado durante a paginação;
- timeout atual: 60 segundos por página.

O corpo é um FetchXML equivalente a:

```xml
<fetch version="1.0" output-format="xml-platform" mapping="logical">
  <entity name="cad_redacao">
    <attribute name="cad_redacaoid"/>
    <attribute name="cad_name"/>
    <attribute name="cad_redacaocomentarios"/>
    <attribute name="cad_corrigidopor"/>
    <attribute name="cad_datacorrecao"/>
    <attribute name="cad_dataentrega"/>
    <attribute name="cad_datainicio"/>
    <attribute name="cad_datalimitetermino"/>
    <attribute name="cad_dataretorno"/>
    <attribute name="cad_inscricao_redacao"/>
    <attribute name="cad_maximocaracteres"/>
    <attribute name="cad_minimocaracteres"/>
    <attribute name="cad_minimocaracterespreenchidos"/>
    <attribute name="cad_nota"/>
    <attribute name="cad_situacao"/>
    <attribute name="cad_observacoes"/>
    <attribute name="cad_temasredacao_redacao"/>
    <attribute name="cad_textoredacao"/>
    <attribute name="cad_totaldecaracteres"/>
    <order attribute="createdon" descending="true"/>
  </entity>
</fetch>
```

O retorno XML é lido a partir de `resultset/result`. Quando `resultset` possui `morerecords="1"`, uma nova requisição é feita com a próxima página. Valores complexos são achatados preferindo `@name` e, na ausência dele, `#text`.

### Importante: o filtro é local

O FetchXML atual não contém condição para a situação. Portanto, todas as redações acessíveis são transferidas do CRM, e só então a aplicação mantém os registros cujo `cad_situacao`, após remoção de espaços e comparação sem diferença entre maiúsculas e minúsculas, seja exatamente `Entregue`.

Um sistema próprio pode reproduzir esse comportamento ou adicionar o filtro equivalente no CRM, desde que preserve a mesma regra funcional.

## Campos necessários para a integração

### Mínimo funcional

| Campo lógico no CRM | Nome usado internamente | Necessidade |
|---|---|---|
| `cad_textoredacao` | `Texto da redação` | **Obrigatório para a IA.** É o conteúdo avaliado. Valor ausente, vazio, `nan`, `none` ou `<na>` interrompe a correção. |
| `cad_temasredacao_redacao` | `Tema da redação` | **Obrigatório para a IA.** O texto é comparado com o tema, inclusive para identificar fuga total ou parcial. Os mesmos valores vazios acima são rejeitados. |
| `cad_situacao` | `Situação` | **Obrigatório para reproduzir a seleção atual.** Somente registros com situação `Entregue` seguem para correção. |
| `cad_redacaoid` | `Id` | **Necessário para rastreabilidade.** Não entra no prompt, mas permite associar a correção ao registro correto no sistema de origem. As chaves `{` e `}` são removidas localmente. |

Em resumo, a chamada isolada à IA precisa apenas do texto e do tema. Para integrar o processo com segurança ao CRM, devem ser consultados também a situação e o identificador da redação.

### Campos consultados atualmente, mas não necessários para avaliar o texto

Os campos abaixo fazem parte da fotografia de dados atual, porém não são usados para compor o prompt da IA:

| Campo no CRM | Nome interno atual |
|---|---|
| `cad_name` | `Assunto` |
| `cad_redacaocomentarios` | `Comentários` |
| `cad_corrigidopor` | `Corrigido por` |
| `cad_datacorrecao` | `Data da correção` |
| `cad_dataentrega` | `Data de entrega` |
| `cad_datainicio` | `Data de início` |
| `cad_datalimitetermino` | `Data limite para o término` |
| `cad_dataretorno` | `Data de retorno` |
| `cad_inscricao_redacao` | `Inscrição` |
| `cad_maximocaracteres` | `Máximo de caracteres` |
| `cad_minimocaracteres` | `Mínimo de caracteres` |
| `cad_minimocaracterespreenchidos` | `Mínimo de caracteres preenchidos` |
| `cad_nota` | `Nota` |
| `cad_observacoes` | `Observações` |
| `cad_totaldecaracteres` | `Total de caracteres` |

Campos cujo nome contém `data` são convertidos para data e hora no fuso `America/Sao_Paulo`. `cad_nota` é convertido para número quando possível. Esses tratamentos não interferem no conteúdo enviado à IA.

## Chamada da IA

Cada redação gera uma requisição independente:

- método: `POST`;
- URL: `https://openrouter.ai/api/v1/chat/completions`;
- `Authorization`: `Bearer {OPENROUTER_KEY}`;
- `Content-Type`: `application/json`;
- modelo: valor de `OPENROUTER_MODEL`;
- `temperature`: `0`;
- timeout atual: 60 segundos.

O conteúdo enviado pelo usuário segue esta estrutura:

```text
Tema da redação:
{cad_temasredacao_redacao}

Texto da redação:
{cad_textoredacao}
```

A instrução de sistema pede uma avaliação equilibrada de:

- coerência temática;
- coesão textual;
- abrangência do conteúdo;
- correção gramatical;
- qualidade geral da escrita;
- fuga total ou parcial ao tema.

O serviço atual trabalha com escala de 0 a 10 e solicita resposta estruturada por JSON Schema. Como indicado no início, o formato e o aproveitamento dessa resposta são deliberadamente omitidos deste documento, pois poderão mudar.

## Pontos de atenção para outro sistema

- Faça a paginação até `morerecords` deixar de ser `1`; consultar apenas a primeira página pode omitir redações.
- Valide tema e texto antes de chamar a IA para evitar consumo desnecessário e interrupções no lote.
- Preserve `cad_redacaoid` junto ao processamento, mesmo sem enviá-lo ao modelo.
- Não confie apenas na ordem `createdon`: use o identificador para correlacionar dados.
- Considere filtrar `Entregue` no FetchXML para reduzir tráfego, mas valide que o valor e o tipo do campo no ambiente do CRM aceitam esse filtro.
- Trate falhas por redação e defina a política de repetição do sistema integrador. No código atual, uma exceção interrompe o lote.
- Avalie os requisitos de privacidade e retenção antes de enviar redações a um provedor externo de IA.
- Não dependa do cache do Streamlit em uma integração própria; implemente atualização, idempotência e observabilidade conforme as necessidades do novo sistema.

## Referências no código

- Interface: `pages/5_Corrigir_redações.py`
- Carregamento e cache: `data_loader.py`, função `carregar_redacoes`
- Campos, preparo e correção: `services/redacoes.py`
- Autenticação, FetchXML e paginação: `services/crm_api.py`
- Configuração: `settings.py`
