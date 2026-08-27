# Checkpoint 2 - Arquitetura Event-Driven com Azure Service Bus

## Objetivo

Este projeto corresponde ao Checkpoint 2 da disciplina de Cloud/Serverless.

O objetivo é evoluir a aplicação desenvolvida no Checkpoint 1, substituindo o modelo de execução baseado em HTTP por uma arquitetura orientada a eventos (Event-Driven).

Nesta implementação foi utilizado o Microsoft Azure, utilizando:

- Azure Functions
- Python
- Azure Service Bus
- Service Bus Topic
- Service Bus Subscription

O professor autorizou a utilização do Azure como alternativa ao Google Cloud Pub/Sub.

---

## Arquitetura

A aplicação utiliza o seguinte fluxo:

```text
                    Publisher
                        |
                        | JSON
                        v
              Azure Service Bus
                        |
                        v
                 Topic: orders
                        |
                        v
          Subscription: orders-subscription
                        |
                        | Event
                        v
              Azure Function
                 process_order
                        |
                        v
                  Processamento

```text

A Azure Function não possui um endpoint HTTP para receber o pedido.

Ela é acionada automaticamente quando uma nova mensagem é disponibilizada na Subscription do Service Bus.

Estrutura do projeto
cloud-serverless-checkpoint2/
│
├── function_app.py
├── requirements.txt
├── host.json
├── send-message.ps1
├── .gitignore
└── README.md


## Pré-requisitos

Para executar o projeto localmente é necessário ter instalado:

- Azure CLI
- Azure Functions Core Tools
- PowerShell
- Python 3.12 ou versão compatível com a aplicação

Também é necessário possuir acesso ao Azure Service Bus utilizado pelo projeto.


## Configuração das credenciais

As credenciais do Azure Service Bus não ficam armazenadas no código-fonte.

O projeto utiliza a configuração:
SERVICE_BUS_CONNECTION

Essa configuração deve conter a connection string do Azure Service Bus.

- Execução local

No PowerShell, configure temporariamente a variável de ambiente:
$env:SERVICE_BUS_CONNECTION="SUA_CONNECTION_STRING"



##  Configuração do ambiente Python

Na pasta do projeto, crie um ambiente virtual:
python -m venv .venv

Ative o ambiente:
.\.venv\Scripts\Activate.ps1

Caso o PowerShell bloqueie a execução do ambiente virtual, utilize:
Set-ExecutionPolicy -Scope Process Bypass

Depois ative novamente:
.\.venv\Scripts\Activate.ps1

##  Instalação das dependências

Com o ambiente virtual ativado:
pip install -r requirements.txt

O arquivo requirements.txt contém:
- azure-functions
- azure-servicebus
- Configuração local da Azure Function

Para executar a Function localmente, configure o arquivo:
local.settings.json

Exemplo:
{
  "IsEncrypted": false,
  "Values": {
    "AzureWebJobsStorage": "UseDevelopmentStorage=true",
    "FUNCTIONS_WORKER_RUNTIME": "python",
    "SERVICE_BUS_CONNECTION": "SUA_CONNECTION_STRING"
  }
}

A connection string deve ser substituída pela credencial válida do Azure Service Bus.

O arquivo local.settings.json está no .gitignore e não deve ser enviado para o repositório.

## Executando a Azure Function localmente

Com o ambiente Python ativado e as dependências instaladas:
func start

A Azure Functions Core Tools deverá identificar a função:
process_order

A função utiliza um Service Bus Topic Trigger.

Não existe endpoint HTTP para executar a função.

Enviando uma mensagem para o Service Bus

Para facilitar o teste, o projeto possui o script:
send-message.ps1

O script publica uma mensagem JSON no Topic:
orders

Execute:
.\send-message.ps1

Exemplo de mensagem:
{
  "order_id": 1001,
  "customer": "cibas",
  "product": "notebook",
  "quantity": 1
}

Ao executar o script, deverá ser exibido:
Mensagem enviada com sucesso!

## Fluxo de processamento

Após o envio da mensagem, o fluxo será:

send-message.ps1
        |
        v
Azure Service Bus
        |
        v
Topic: orders
        |
        v
orders-subscription
        |
        v
Azure Function
process_order
        |
        v
Processamento da mensagem

A função recebe o conteúdo da mensagem e extrai os dados do pedido.

## Código da Function

A função principal está localizada em:
function_app.py

O trigger utilizado é:
@app.service_bus_topic_trigger(
    arg_name="message",
    topic_name="orders",
    subscription_name="orders-subscription",
    connection="SERVICE_BUS_CONNECTION"
)

A função recebe a mensagem:
def process_order(message: func.ServiceBusMessage):

O conteúdo da mensagem é convertido para texto e depois para um objeto JSON:
body = message.get_body().decode("utf-8")
order = json.loads(body)

Depois os dados do pedido são registrados nos logs.

Após o envio da mensagem, os logs da Function deverão apresentar informações semelhantes a:

================================
Pedido recebido do Service Bus
================================

Order ID: 1001
Cliente: cibas
Produto: notebook
Quantidade: 1

Pedido processado com sucesso.

A execução deverá ser finalizada com sucesso:
   Executed 'Functions.process_order' (Succeeded)