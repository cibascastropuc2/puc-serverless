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

# Cenários de Teste e Validação

Esta seção apresenta os três principais cenários utilizados para validar a arquitetura do projeto:

1. **Teste de sucesso** — processamento completo de um pedido.
2. **Teste de idempotência** — tentativa de processar novamente um pedido já concluído.
3. **Teste de retry e tratamento de falha** — simulação de erro durante o processamento e execução das tentativas automáticas.

---

## 1. Preparação do ambiente

### 1.1 Variáveis utilizadas

No PowerShell:

```powershell

$env:AZURE_OPENAI_ENDPOINT="https://ai-checkpoint-final-cibas.cognitiveservices.azure.com/"
$env:AZURE_OPENAI_DEPLOYMENT="gpt-4-1-mini"
$env:SERVICE_BUS_CONNECTION = (Get-Content .\local.settings.json | ConvertFrom-Json).Values.SERVICE_BUS_CONNECTION
$env:languageWorkers__python__path = "$PWD\.venv\Scripts\python.exe"
```

> As connection strings e credenciais são mantidas no `local.settings.json` e não devem ser versionadas no Git.

---

### 1.2 Iniciar o Azurite

Em um terminal separado:

```powershell
azurite
```

O Azurite fornece os serviços locais necessários para o ambiente de desenvolvimento.

---

### 1.3 Criar o ambiente virtual Python

O projeto utiliza Python 3.11.

```powershell
py -3.11 -m venv .venv
```

Ativar o ambiente:

```powershell
.\.venv\Scripts\Activate.ps1
```

Confirmar a versão:

```powershell
python --version
```

Resultado esperado:

```text
Python 3.11.x
```

Atualizar o `pip`:

```powershell
python -m pip install --upgrade pip
```

Instalar as dependências:

```powershell
python -m pip install -r requirements.txt
```

---

### 1.4 Validar Python e Durable Functions

Executar:

```powershell
python -c "import sys; print(sys.executable); print(sys.version); import azure.durable_functions; print('Durable Functions OK')"
```

Resultado esperado:

```text
Durable Functions OK
```

Validar também o Azure Service Bus:

```powershell
python -c "import azure.servicebus; print('Azure Service Bus OK')"
```

Resultado esperado:

```text
Azure Service Bus OK
```

---

### 1.5 Iniciar o Azure Functions Host

```powershell
func start
```

O host deve carregar as funções do projeto.

Entre as funções esperadas estão:

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

Para registrar os logs em arquivo:

```powershell
func start 2>&1 | Tee-Object -FilePath .\func.log
```

O arquivo `func.log` será utilizado para comprovar os cenários de teste.

---

# 2. Cenário 1 — Teste de Sucesso

## Objetivo

Validar o fluxo completo de processamento de um pedido, incluindo:

* Azure Service Bus;
* Azure Functions;
* Durable Functions;
* validação;
* controle de idempotência;
* registro do pedido;
* processamento;
* análise utilizando Azure OpenAI;
* finalização;
* persistência no Azure Table Storage.

---

## 2.1 Enviar o pedido

Com o Functions Host em execução, abrir outro PowerShell na pasta do projeto.

Se necessário, ativar o ambiente virtual:

```powershell
.\.venv\Scripts\Activate.ps1
```

Enviar o pedido:

```powershell
python -c "from azure.servicebus import ServiceBusClient, ServiceBusMessage; import json, os; c=ServiceBusClient.from_connection_string(os.environ['SERVICE_BUS_CONNECTION']); s=c.get_topic_sender(topic_name='orders-topic'); s.send_messages(ServiceBusMessage(json.dumps({'order_id':1006,'customer':'Cibas','product':'Notebook','quantity':4}))); s.close(); c.close(); print('Pedido 1006 enviado')"
```

Resultado esperado:

```text
Pedido 1006 enviado
```

---

## 2.2 Fluxo esperado

O pedido deve percorrer as seguintes etapas:

```text
Service Bus
     |
     v
process_order
     |
     v
order_orchestrator
     |
     +--> validate_order
     |
     +--> check_idempotency
     |
     +--> register_order
     |
     +--> process_order_activity
     |
     +--> analyze_order_with_ai
     |
     +--> finish_order
     |
     v
Azure Table Storage
     |
     v
COMPLETED
```

---

## 2.3 Acompanhar o processamento

Pesquisar o pedido no log:

```powershell
Select-String -Path .\func.log -Pattern "order-1006" -Context 1,2
```

Também é possível verificar especificamente a etapa de finalização:

```powershell
Select-String -Path .\func.log -Pattern "finish_order" -Context 3,5
```

Devem aparecer as principais etapas:

```text
order_orchestrator
validate_order
check_idempotency
register_order
process_order_activity
analyze_order_with_ai
finish_order
```

Na etapa de IA, deve aparecer algo semelhante a:

```text
Executed 'Functions.analyze_order_with_ai' (Succeeded
```

Ao final da orquestração:

```text
RuntimeStatus: Completed
```

---

## 2.4 Consultar o pedido no Table Storage

A consulta utiliza a connection string armazenada no `local.settings.json`, sem exibi-la no terminal:

```powershell
python -c "import json; from azure.data.tables import TableServiceClient; c=json.load(open('local.settings.json'))['Values']['ORDERS_STORAGE_CONNECTION']; t=TableServiceClient.from_connection_string(c).get_table_client('Orders'); print(t.get_entity(partition_key='orders', row_key='1006'))"
```

Resultado esperado:

```text
{
    'PartitionKey': 'orders',
    'RowKey': '1006',
    'status': 'COMPLETED',
    'ai_status': 'ANALYZED',
    'ai_analysis': '...'
}
```

Esse resultado comprova que o pedido foi processado, analisado pela IA e persistido no Azure Table Storage.

---

# 3. Cenário 2 — Teste de Idempotência

## Objetivo

Validar que um pedido já processado não seja executado novamente.

Nesse cenário, utilizamos o pedido `1006`, que já possui:

```text
status = COMPLETED
```

O mecanismo `check_idempotency` deve identificar que o pedido já foi processado.

---

## 3.1 Reenviar o mesmo pedido

Enviar novamente exatamente o mesmo pedido:

```powershell
python -c "import json; from azure.servicebus import ServiceBusClient, ServiceBusMessage; c=json.load(open('local.settings.json'))['Values']['SERVICE_BUS_CONNECTION']; msg=ServiceBusMessage(json.dumps({'order_id':1006,'customer':'Cibas','product':'Notebook','quantity':4})); client=ServiceBusClient.from_connection_string(c); sender=client.get_topic_sender(topic_name='orders-topic'); sender.send_messages(msg); sender.close(); client.close(); print('Pedido 1006 reenviado')"
```

Resultado:

```text
Pedido 1006 reenviado
```

---

## 3.2 Fluxo esperado

O pedido deve passar novamente pelo início da arquitetura:

```text
Service Bus
     |
     v
process_order
     |
     v
order_orchestrator
     |
     v
validate_order
     |
     v
check_idempotency
     |
     v
Pedido 1006 já está COMPLETED
     |
     v
ALREADY_PROCESSED
```

A execução deve ser interrompida nesse ponto.

Não devem ser executadas novamente as atividades:

```text
register_order
process_order_activity
analyze_order_with_ai
finish_order
```

---

## 3.3 Comprovar pelo log

Pesquisar o pedido:

```powershell
Select-String -Path .\func.log -Pattern "order-1006" -Context 2,3
```

Pesquisar especificamente os eventos de idempotência:

```powershell
Select-String -Path .\func.log -Pattern "already_processed|ALREADY_PROCESSED|idempot"
```

O resultado deve demonstrar que `check_idempotency` identificou o pedido como já processado.

---

## 3.4 Confirmar que o registro permanece COMPLETED

Consultar novamente o pedido:

```powershell
python -c "import json; from azure.data.tables import TableServiceClient; c=json.load(open('local.settings.json'))['Values']['ORDERS_STORAGE_CONNECTION']; t=TableServiceClient.from_connection_string(c).get_table_client('Orders'); print(t.get_entity(partition_key='orders', row_key='1006'))"
```

O status deve continuar:

```text
status = COMPLETED
```

A validação demonstra que o mesmo pedido pode ser recebido novamente pelo sistema sem provocar um novo processamento.

---

# 4. Cenário 3 — Teste de Retry e Tratamento de Falha

## Objetivo

Validar o mecanismo de retry do Durable Functions e o tratamento de uma falha após o número máximo de tentativas.

Para esse teste, a função `process_order_activity` possui uma falha proposital para o pedido `9999`.

---

## 4.1 Configuração do Retry

A orquestração utiliza:

```text
first_retry_interval_in_milliseconds = 5000
max_number_of_attempts = 3
```

Portanto, são permitidas até três tentativas de execução da atividade.

Fluxo esperado:

```text
Tentativa 1
    |
    v
FAIL
    |
    | aproximadamente 5 segundos
    v
Tentativa 2
    |
    v
FAIL
    |
    | aproximadamente 5 segundos
    v
Tentativa 3
    |
    v
FAIL
    |
    v
register_failure
    |
    v
status = FAILED
```

> O intervalo observado nos logs pode ser ligeiramente superior a 5 segundos devido ao agendamento e processamento do Durable Functions.

---

## 4.2 Enviar o pedido de teste

Enviar o pedido `9999`:

```powershell
python -c "import json; from azure.servicebus import ServiceBusClient, ServiceBusMessage; c=json.load(open('local.settings.json'))['Values']['SERVICE_BUS_CONNECTION']; msg=ServiceBusMessage(json.dumps({'order_id':9999,'customer':'Cibas','product':'Notebook','quantity':4})); client=ServiceBusClient.from_connection_string(c); sender=client.get_topic_sender(topic_name='orders-topic'); sender.send_messages(msg); sender.close(); client.close(); print('Pedido 9999 enviado')"
```

Resultado:

```text
Pedido 9999 enviado
```

---

## 4.3 Comprovar as três tentativas

Pesquisar o pedido no log:

```powershell
Select-String -Path .\func.log -Pattern "order-9999" -Context 2,3
```

Pesquisar especificamente a atividade que apresenta a falha:

```powershell
Select-String -Path .\func.log -Pattern "process_order_activity" -Context 3,5
```

Também pode ser utilizado:

```powershell
Select-String -Path .\func.log -Pattern "retry|Retry|failed|FAILED" -Context 2,3
```

O log deve demonstrar três execuções de:

```text
process_order_activity
```

com falha em cada tentativa.

---

## 4.4 Validar o resultado final

Depois das três tentativas, o Durable Functions deve executar:

```text
register_failure
```

e registrar o pedido como:

```text
status = FAILED
```

Consultar o Table Storage:

```powershell
python -c "import json; from azure.data.tables import TableServiceClient; c=json.load(open('local.settings.json'))['Values']['ORDERS_STORAGE_CONNECTION']; t=TableServiceClient.from_connection_string(c).get_table_client('Orders'); print(t.get_entity(partition_key='orders', row_key='9999'))"
```

Resultado esperado:

```text
{
    'PartitionKey': 'orders',
    'RowKey': '9999',
    'status': 'FAILED',
    'error': '...'
}
```

Esse resultado comprova que:

* a atividade apresentou falha;
* o Durable Functions executou as tentativas configuradas;
* após atingir o limite de tentativas, o fluxo não continuou normalmente;
* `register_failure` registrou a falha;
* o pedido foi persistido com `status = FAILED`.

---

# 5. Resumo dos cenários

| Cenário      |           Pedido | Resultado esperado         | Componentes validados                                        |
| ------------ | ---------------: | -------------------------- | ------------------------------------------------------------ |
| Sucesso      |           `1006` | `COMPLETED`                | Service Bus, Durable Functions, Azure OpenAI e Table Storage |
| Idempotência | `1006` reenviado | `ALREADY_PROCESSED`        | `check_idempotency`                                          |
| Retry/Falha  |           `9999` | `FAILED` após 3 tentativas | Retry do Durable Functions e `register_failure`              |

## Evidências obtidas

### Cenário 1 — Sucesso

```text
1006
   |
   +--> validate_order
   +--> check_idempotency
   +--> register_order
   +--> process_order_activity
   +--> analyze_order_with_ai
   +--> finish_order
   |
   v
COMPLETED
```

O registro final contém:

```text
status    = COMPLETED
ai_status = ANALYZED
ai_analysis = resultado gerado pelo Azure OpenAI
```

### Cenário 2 — Idempotência

```text
1006 reenviado
      |
      v
check_idempotency
      |
      v
já está COMPLETED
      |
      v
ALREADY_PROCESSED
```

As etapas de processamento e análise não são executadas novamente.

### Cenário 3 — Retry

```text
9999
 |
 +--> tentativa 1 --> FAIL
 |
 +--> tentativa 2 --> FAIL
 |
 +--> tentativa 3 --> FAIL
 |
 v
register_failure
 |
 v
FAILED
```

Os três cenários demonstram os principais comportamentos da arquitetura: **processamento normal, proteção contra duplicidade e recuperação controlada de falhas**.
