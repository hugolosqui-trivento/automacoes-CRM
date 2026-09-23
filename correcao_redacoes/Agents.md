# Resumo
Criação de um corretor de redações por ia.


## Tarefas

-criar módulo python responsável pela chamada a api, com código simples e sem programação defensiva excessiva de tratamento de erros.
- Em seguida, acrecente em analise.ipynb a chamada a api , que deve fornecer o texto da redação e enviá-lo ao modelo. O retorne deve ser a nota conforme descrito mais abaixo.

## Requisitos
- Utilizar modelos hospedados na openrouter a partir da chave OPENROUTER_API



## Parametrização da Correção por IA
Atualmente, a correção automática por inteligência artificial utiliza um único modelo de parametrização padrão.

Esse modelo de ia deve avaliar de acordo com seguintes critérios:

- Coerência temática
- Abrangência do conteúdo
- Correção gramatical
- Qualidade geral da escrita

Ao final, deve retornar uma nota de 1 a 10.