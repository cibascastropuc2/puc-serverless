# Checkpoint 3 - Orquestração de Serviços com Azure Durable Functions

## Objetivo

EEste projeto corresponde ao Checkpoint 3 da disciplina de Cloud/Serverless.

O objetivo é evoluir a aplicação desenvolvida nos checkpoints anteriores, criando uma arquitetura de orquestração de serviços serverless, permitindo controlar o fluxo de processamento de pedidos, aplicar regras de idempotência, realizar retry em caso de falhas e encaminhar pedidos que não puderam ser processados para uma fila de falhas.

Nesta implementação foi utilizado o Microsoft Azure, utilizando::

- Azure Functions
- Python
- Azure Durable Functions
- Azure Service Bus
- Azure Table Storage
- Service Bus Queue
- Durable Functions Orchestrator
- Activity Functions

A proposta original do checkpoint utiliza o Google Cloud Workflows. O professor autorizou a utilização do Azure como alternativa, sendo utilizado o Azure Durable Functions para realizar a orquestração do fluxo.

---

## Arquitetura

A aplicação utiliza o seguinte fluxo:

```text
                     Pedido
                       |
                       | JSON
                       v
              Azure Service Bus
                       |
                       v
                  Orchestrator
                order_orchestrator
                       |
                       v
              validate_order_activity
                       |
                       v
              process_order_activity
                       |
                 +-----+-----+
                 |           |
              Sucesso       Falha
                 |           |
                 |           v
                 |          Retry
                 |           |
                 |      +----+----+
                 |      |         |
                 |   Sucesso    Falha
                 |                 |
                 |                 v
                 |          Falha definitiva
                 |                 |
                 |                 v
                 |       register_failure
                 |                 |
                 |                 v
                 |          failed-orders
                 |
                 v
              Concluído

```
---

## Componentes

Responsável pelo recebimento e comunicação das mensagens relacionadas aos pedidos.

A mensagem contém os dados do pedido em formato JSON.

Exemplo:

{
    "order_id": "1001",
    "customer": "cibas",
    "product": "notebook",
    "quantity": 1
}

---

## Componentes

O order_orchestrator é responsável por controlar a execução do fluxo.

Ele determina a ordem em que as Activities serão executadas e também realiza o tratamento das falhas.

Fluxo principal:

```text
Pedido
  |
  v
Validação
  |
  v
Processamento
  |
  v
Sucesso

Em caso de erro:

Processamento
     |
     v
   Falha
     |
     v
   Retry
     |
     v
Falha definitiva
     |
     v
register_failure
     |
     v
failed-orders

```

---

## Activities

As responsabilidades do processamento foram separadas em diferentes Activities.

validate_order_activity

Responsável por validar os dados recebidos do pedido antes que o processamento seja iniciado.


---

## process_order_activity

Responsável pelo processamento do pedido.

Essa Activity também está sujeita ao mecanismo de retry configurado no Orchestrator.

Para validar o funcionamento do retry, foi utilizado um erro proposital durante os testes:

raise Exception("Erro proposital para testar retry")

---

## register_failure

Responsável pelo tratamento da falha definitiva.

Quando todas as tentativas de retry são esgotadas, essa Activity é executada e o pedido é enviado para:

failed-orders

Exemplo de log obtido durante o teste:

Falha definitiva no pedido 9999
Pedido 9999 enviado para failed-orders.


---

## Retry

O projeto utiliza o mecanismo de retry do Azure Durable Functions.

Quando ocorre uma falha durante a execução de uma Activity, o Orchestrator realiza novas tentativas de execução de acordo com a configuração definida.

O fluxo é:

```text
process_order_activity
          |
          v
        Falha
          |
          v
       Retry
          |
          v
    Nova tentativa
          |
          +------> Sucesso
          |
          +------> Falha
                       |
                       v
                 Nova tentativa
                       |
                       +------> Sucesso
                       |
                       +------> Falha definitiva
```
---

## Idempotência

O projeto implementa uma regra de idempotência para evitar que um mesmo pedido seja processado mais de uma vez.

Para isso, é utilizado o Azure Table Storage para armazenar informações dos pedidos que já foram processados.

Antes de processar um pedido, o sistema verifica se o order_id já foi registrado.

```text
                 Pedido
                    |
                    v
          Verifica order_id
                    |
             +------+------+
             |             |
            SIM           NÃO
             |             |
             v             v
       Não processa     Processa
                           |
                           v
                    Registra pedido
```

Dessa forma, caso o mesmo pedido seja recebido novamente, o processamento duplicado é evitado.

---

## Tratamento de Falhas

Quando o processamento de um pedido falha, o Orchestrator tenta executar novamente a Activity de processamento utilizando o mecanismo de retry.

Caso todas as tentativas sejam esgotadas, o pedido é considerado como uma falha definitiva.

Nesse cenário, a Activity register_failure é executada e o pedido é encaminhado para a estrutura failed-orders.

Exemplo:

```text
Pedido 9999
     |
     v
process_order_activity
     |
     v
Erro proposital
     |
     v
Retry
     |
     v
Retry
     |
     v
Falha definitiva
     |
     v
register_failure
     |
     v
failed-orders

```

---

## Testes

Foram realizados testes para validar os principais requisitos do projeto.


---

## Teste 1 - Processamento com sucesso

Foi utilizado um pedido válido:

{
    "order_id": "1001",
    "customer": "cibas",
    "product": "notebook",
    "quantity": 1
}

Resultado esperado:

```text
Pedido recebido
      |
      v
Pedido validado
      |
      v
Pedido processado
      |
      v
Sucesso

```

---

## Teste 2 - Idempotência

O mesmo pedido é enviado novamente utilizando o mesmo order_id.

Resultado esperado:

```text
Pedido 1001 recebido
       |
       v
Pedido já processado
       |
       v
Processamento duplicado evitado

```

---

## Teste 3 - Retry e Falha Definitiva

Foi utilizado o pedido 9999 para provocar uma falha proposital durante o processamento.

Erro utilizado:

raise Exception("Erro proposital para testar retry")

O log apresentou:

Falha definitiva no pedido 9999
Pedido 9999 enviado para failed-orders.

A Activity register_failure foi executada com sucesso e o Orchestrator terminou com:

RuntimeStatus: Completed

Esse teste demonstra o funcionamento do mecanismo de:

- Retry
- Tratamento de exceção
- Falha definitiva
- Encaminhamento para failed-orders

---

## Execução Local

Para executar o projeto localmente, é necessário possuir:

- Python 3.11
- Azure Functions Core Tools
- Azure CLI
- PowerShell

Primeiro, instale as dependências:

pip install -r requirements.txt

Em seguida, configure o arquivo:

local.settings.json

Esse arquivo deve conter as configurações necessárias para execução local.

O arquivo local.settings.json não deve ser enviado para o GitHub, pois pode conter informações sensíveis.

Para iniciar as Azure Functions localmente:

func start


---

## Segurança

Nenhuma credencial, chave de acesso, token ou connection string real deve ser armazenada no repositório público.

O arquivo:
```text
local.settings.json
```

deve permanecer no .gitignore.

Foi disponibilizado um arquivo de exemplo:

```text
local.settings.json.example
```

Esse arquivo contém apenas a estrutura necessária para configuração do ambiente, sem credenciais reais.

---

## Resultado

A implementação evolui a arquitetura dos checkpoints anteriores para um modelo baseado em orquestração de serviços serverless.

O Azure Durable Functions é responsável por controlar o fluxo de execução, enquanto as Activities realizam as operações individuais.

A solução implementa:

- Orquestração de serviços
- Processamento de pedidos
- Validação
- Idempotência
- Retry automático
- Tratamento de falhas
- Falha definitiva
- failed-orders
- Comunicação através do Azure Service Bus
- Persistência para controle de processamento
- Execução local
- Boas práticas de segurança

```text
              Azure Service Bus
                     |
                     v
             Order Orchestrator
                     |
          +----------+----------+
          |                     |
          v                     v
      Validation            Processing
                                |
                           +----+----+
                           |         |
                        Sucesso     Falha
                           |         |
                           |       Retry
                           |         |
                           |    Falha definitiva
                           |         |
                           |         v
                           |   Register Failure
                           |         |
                           |         v
                           |   failed-orders
                           |
                           v
                        Concluído

```

---

## Conclusão

O Checkpoint 3 demonstra a evolução da aplicação para uma arquitetura serverless orquestrada, utilizando Azure Durable Functions para controlar o fluxo entre diferentes serviços.

A implementação permite lidar com processamento normal, evitar duplicidades por meio de idempotência, realizar novas tentativas automaticamente em caso de falhas e encaminhar pedidos que não puderam ser processados para failed-orders.

Dessa forma, a solução atende aos principais requisitos propostos para o Checkpoint 3.