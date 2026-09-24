# Projeto Final — Arquitetura Serverless Orientada a Eventos com IA

Projeto desenvolvido para a disciplina de Cloud Computing / Serverless da PUC Minas, consolidando os conceitos e implementações desenvolvidos nos checkpoints anteriores em uma arquitetura orientada a eventos utilizando serviços Azure.

A solução utiliza Azure Functions, Durable Functions, Azure Service Bus, Azure Table Storage e Azure OpenAI para processar pedidos de forma assíncrona, resiliente e com análise inteligente baseada em IA.

---

## 1. Objetivo do projeto

O objetivo é implementar uma solução serverless orientada a eventos capaz de:

* Receber pedidos de forma assíncrona;
* Processar os pedidos utilizando Azure Functions;
* Orquestrar as etapas utilizando Durable Functions;
* Validar os dados recebidos;
* Garantir idempotência no processamento;
* Registrar o pedido durante o processamento;
* Executar uma etapa de processamento;
* Utilizar IA para analisar o pedido;
* Persistir o resultado da análise;
* Finalizar o processamento;
* Registrar falhas;
* Permitir retry automático das atividades;
* Integrar conceitos de CI/CD desenvolvidos nos checkpoints anteriores.

---

# 2. Arquitetura

A arquitetura implementada utiliza o seguinte fluxo:

```text
                         ┌──────────────────────┐
                         │      Cliente         │
                         │    / Produtor        │
                         └──────────┬───────────┘
                                    │
                                    │ Pedido
                                    ▼
                         ┌──────────────────────┐
                         │   Azure Service Bus  │
                         │      orders-topic    │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  process_order       │
                         │  Azure Function      │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ Durable Functions    │
                         │ order_orchestrator   │
                         └──────────┬───────────┘
                                    │
                  ┌─────────────────┼──────────────────┐
                  │                 │                  │
                  ▼                 ▼                  ▼
          ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐
          │ validate     │  │ check        │  │ register_order  │
          │ _order       │  │ idempotency  │  │                 │
          └──────┬───────┘  └──────┬───────┘  └────────┬────────┘
                 │                 │                   │
                 └─────────────────┼───────────────────┘
                                   │
                                   ▼
                         ┌──────────────────────┐
                         │ process_order        │
                         │ _activity            │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ analyze_order_with   │
                         │ _ai                  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │    Azure OpenAI      │
                         │     GPT-4.1-mini     │
                         └──────────┬───────────┘
                                    │
                              AI analysis
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │     finish_order     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  Azure Table Storage │
                         │       Orders         │
                         └──────────────────────┘


                    Em caso de falha
                            │
                            ▼
                  ┌──────────────────────┐
                  │  register_failure    │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ failed-orders Queue  │
                  └──────────────────────┘
```

---

# 3. Serviços Azure utilizados

## Azure Functions

As Azure Functions implementam os componentes da aplicação serverless.

Principais funções:

* `process_order`
* `order_orchestrator`
* `validate_order`
* `check_idempotency`
* `register_order`
* `process_order_activity`
* `analyze_order_with_ai`
* `finish_order`
* `register_failure`

---

## Azure Service Bus

O Service Bus é utilizado como mecanismo de comunicação assíncrona entre o produtor e a aplicação.

### Topic

```text
orders-topic
```

### Subscription

```text
orders-subscription
```

Os pedidos publicados no tópico são consumidos pela Azure Function `process_order`.

Também existe um fluxo de tratamento de falhas utilizando a fila:

```text
failed-orders
```

---

## Durable Functions

O Durable Functions é responsável pela orquestração do processamento.

O orquestrador:

```text
order_orchestrator
```

coordena as atividades na ordem correta e permite:

* Execução controlada das etapas;
* Persistência do estado da orquestração;
* Retry automático;
* Tratamento de exceções;
* Continuidade do processamento após falhas temporárias.

As atividades utilizam `RetryOptions` com:

```text
first_retry_interval = 5 segundos
max_attempts = 3
```

---

# 4. Processamento do pedido

O processamento segue as seguintes etapas.

## 4.1 Recepção

A mensagem chega ao:

```text
orders-topic
```

e é consumida pela subscription:

```text
orders-subscription
```

A Azure Function:

```text
process_order
```

recebe a mensagem e inicia uma nova instância do Durable Orchestrator.

---

## 4.2 Validação

A atividade:

```text
validate_order
```

verifica os dados obrigatórios do pedido e valida se a quantidade informada é válida.

Exemplo:

```json
{
  "order_id": 1006,
  "customer": "Cibas",
  "product": "Notebook",
  "quantity": 4
}
```

---

## 4.3 Idempotência

A atividade:

```text
check_idempotency
```

consulta a tabela `Orders`.

Caso o pedido já tenha sido processado com status:

```text
COMPLETED
```

o sistema evita o processamento duplicado.

---

## 4.4 Registro do processamento

A atividade:

```text
register_order
```

registra o pedido no Azure Table Storage com:

```text
status = PROCESSING
```

---

## 4.5 Processamento

A atividade:

```text
process_order_activity
```

executa a etapa principal de processamento do pedido.

Essa atividade também possui retry automático por meio do Durable Functions.

---

# 5. Integração com Azure OpenAI

A atividade:

```text
analyze_order_with_ai
```

integra a aplicação ao Azure OpenAI.

O modelo utilizado é:

```text
gpt-4-1-mini
```

A IA recebe informações do pedido e produz uma análise contendo informações como:

* Categoria;
* Prioridade;
* Justificativa.

Exemplo de resultado produzido durante o teste:

```text
1. Categoria: Equipamentos eletrônicos
2. Prioridade: MEDIUM
3. Justificativa: Pedido de quantidade moderada de notebooks,
importante para operações, mas sem urgência explícita.
```

A análise produzida pela IA é posteriormente persistida no Azure Table Storage.

---

# 6. Persistência

Os dados são armazenados no Azure Table Storage.

### Storage Account

```text
stfinalcibas2026
```

### Tabela

```text
Orders
```

Cada pedido utiliza:

```text
PartitionKey = orders
RowKey = order_id
```

Para um pedido processado com sucesso, são armazenadas informações como:

```text
status
ai_status
ai_analysis
```

Exemplo:

```text
PartitionKey: orders
RowKey: 1006
status: COMPLETED
ai_status: ANALYZED
ai_analysis: resultado produzido pelo Azure OpenAI
```

---

# 7. Tratamento de falhas

A arquitetura utiliza dois mecanismos principais para aumentar a resiliência.

## Retry

As atividades do Durable Functions são executadas utilizando retry automático.

Configuração:

```text
Intervalo inicial: 5 segundos
Número máximo de tentativas: 3
```

Isso permite que falhas temporárias sejam tratadas automaticamente.

---

## Registro de falhas

Quando ocorre uma exceção que impede a conclusão do processamento, o fluxo utiliza:

```text
register_failure
```

A atividade registra o pedido como:

```text
FAILED
```

e armazena informações sobre o erro.

O pedido também pode ser encaminhado para:

```text
failed-orders
```

permitindo tratamento posterior.

---

# 8. Idempotência

A aplicação implementa controle de idempotência utilizando o Azure Table Storage.

Antes de processar um pedido, a aplicação verifica se já existe uma entidade correspondente ao `order_id`.

Caso o pedido esteja:

```text
COMPLETED
```

o processamento é interrompido e o sistema retorna:

```text
ALREADY_PROCESSED
```

Essa estratégia evita processamento duplicado de uma mesma ordem.

---

# 9. Teste de funcionamento

Foi realizado um teste completo utilizando o pedido:

```json
{
  "order_id": 1006,
  "customer": "Cibas",
  "product": "Notebook",
  "quantity": 4
}
```

O processamento percorreu o fluxo:

```text
Service Bus
     ↓
process_order
     ↓
order_orchestrator
     ↓
validate_order
     ↓
check_idempotency
     ↓
register_order
     ↓
process_order_activity
     ↓
analyze_order_with_ai
     ↓
Azure OpenAI
     ↓
finish_order
     ↓
Azure Table Storage
```

Resultado armazenado:

```text
status    = COMPLETED
ai_status = ANALYZED
```

A análise produzida pelo Azure OpenAI também foi persistida na tabela `Orders`.

Esse teste comprova a integração entre mensageria, processamento serverless, orquestração, IA e persistência.

---

# 10. Estrutura do projeto

Estrutura principal:

```text
cloud-serverless-final/
│
├── function_app.py
├── activities.py
├── requirements.txt
├── host.json
├── local.settings.json
├── README.md
│
├── .github/
│   └── workflows/
│       └── azure-function-deploy.yml
│
└── .venv/
```

### `function_app.py`

Contém:

* Trigger do Service Bus;
* Durable Client;
* Orchestrator;
* Definição das funções serverless.

### `activities.py`

Contém:

* Validação;
* Idempotência;
* Registro;
* Processamento;
* Integração com Azure OpenAI;
* Finalização;
* Tratamento de falhas.

### `requirements.txt`

Define as dependências Python utilizadas pela aplicação.

---

# 11. Configuração

As configurações locais são armazenadas em:

```text
local.settings.json
```

As informações sensíveis não devem ser versionadas no Git.

Entre as configurações utilizadas estão:

```text
SERVICE_BUS_CONNECTION
ORDERS_STORAGE_CONNECTION
AZURE_OPENAI_ENDPOINT
AZURE_OPENAI_DEPLOYMENT
```

As credenciais devem ser configuradas por meio de variáveis de ambiente ou configurações protegidas no ambiente Azure.

---

# 12. Execução local

Criar e ativar o ambiente virtual:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Instalar as dependências:

```powershell
pip install -r requirements.txt
```

Iniciar a aplicação:

```powershell
func start
```

A aplicação deverá carregar as funções:

```text
process_order
order_orchestrator
validate_order
check_idempotency
register_order
process_order_activity
analyze_order_with_ai
finish_order
register_failure
```

---

# 13. CI/CD

O projeto também incorpora os conceitos desenvolvidos no checkpoint de CI/CD.

O repositório utiliza GitHub Actions para automatizar o processo de deployment da Azure Function.

O workflow está localizado em:

```text
.github/workflows/azure-function-deploy.yml
```

A estratégia utiliza autenticação baseada em identidade federada/OIDC, evitando a necessidade de armazenar credenciais permanentes da Azure no código-fonte.

---

# 14. Segurança

A solução considera alguns princípios de segurança:

* Credenciais não devem ser armazenadas no código;
* Segredos devem permanecer fora do repositório;
* Utilização de identidade gerenciada quando aplicável;
* Autenticação baseada em identidade para serviços Azure;
* Separação das configurações de ambiente;
* Controle de acesso aos recursos Azure;
* Uso de variáveis de ambiente para configurações sensíveis.

---

# 15. Benefícios da arquitetura

A arquitetura foi construída utilizando características fundamentais do modelo serverless:

### Escalabilidade

As Azure Functions permitem que o processamento seja executado sob demanda.

### Desacoplamento

O Azure Service Bus separa o produtor do consumidor.

### Resiliência

Durable Functions fornece controle do estado e retry das atividades.

### Processamento assíncrono

Os pedidos não precisam ser processados de forma síncrona pelo produtor.

### Inteligência

O Azure OpenAI adiciona uma etapa de análise inteligente ao processamento.

### Persistência

O Azure Table Storage mantém o estado e o resultado do processamento.

### Observabilidade

Os logs das Azure Functions permitem acompanhar cada etapa da execução.

---

# 16. Tecnologias utilizadas

* Python 3.11
* Azure Functions
* Azure Durable Functions
* Azure Service Bus
* Azure Table Storage
* Azure OpenAI
* GPT-4.1-mini
* GitHub Actions
* Azure
* Git/GitHub

---

# 17. Conclusão

O projeto consolida os conceitos desenvolvidos ao longo dos checkpoints em uma arquitetura serverless orientada a eventos.

A solução utiliza mensageria assíncrona para receber pedidos, Durable Functions para coordenar o processamento, Azure OpenAI para realizar a análise inteligente e Azure Table Storage para persistir o resultado.

O fluxo foi validado com processamento completo de um pedido, incluindo a execução da análise por IA e a persistência do resultado:

```text
Service Bus
     ↓
Azure Functions
     ↓
Durable Functions
     ↓
Azure OpenAI
     ↓
Azure Table Storage
```

A implementação demonstra como diferentes serviços gerenciados da Azure podem ser combinados para construir uma aplicação distribuída, assíncrona, resiliente e orientada a eventos.
