# Checkpoint 4 — Observabilidade do Pipeline Serverless

## 1. Sobre o projeto

Este projeto corresponde ao **Checkpoint 4** da disciplina de Computação Serverless.

O objetivo desta etapa é evoluir o pipeline desenvolvido nos checkpoints anteriores, adicionando **observabilidade**, por meio de:

* logging estruturado;
* métricas de execução;
* rastreamento das etapas da orquestração;
* monitoramento de falhas e retries;
* análise de performance;
* análise de custos;
* identificação de otimizações técnicas.

A implementação foi realizada utilizando serviços nativos da **Microsoft Azure**.

---

# 2. Arquitetura

O pipeline utiliza:

* **Azure Functions**
* **Azure Durable Functions**
* **Azure Service Bus**
* **Azure Storage / Table Storage**
* **Azure Application Insights**
* **Azure Monitor**

Fluxo principal:

```text
                     Azure Service Bus
                            │
                            │ orders
                            ▼
                  ┌─────────────────────┐
                  │    process_order    │
                  │   Service Bus       │
                  │      Trigger        │
                  └──────────┬──────────┘
                             │
                             ▼
                  ┌─────────────────────┐
                  │  order_orchestrator │
                  │  Durable Function   │
                  └──────────┬──────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
 ┌────────────────┐ ┌──────────────────┐ ┌────────────────┐
 │ validate_order │ │ check_idempotency│ │ register_order │
 └────────────────┘ └──────────────────┘ └────────────────┘
                                                  │
                                                  ▼
                                    ┌────────────────────────┐
                                    │ process_order_activity  │
                                    └────────────┬───────────┘
                                                 │
                                                 ▼
                                      ┌──────────────────┐
                                      │   finish_order   │
                                      └────────┬─────────┘
                                               │
                                               ▼
                                           COMPLETED

Em caso de falha:

                    order_orchestrator
                            │
                            ▼
                    register_failure
                            │
                            ▼
                     failed-orders
```

---

# 3. Recursos Azure

## Function App

```text
func-checkpoint4-cibas2026
```

Runtime:

```text
Python 3.11
```

Plano:

```text
Flex Consumption
```

Região:

```text
East US 2
```

## Resource Group

```text
VisualStudioOnline-FBDD2D6D4E494DF1BED16F161CD7EC5B
```

## Service Bus

Namespace:

```text
sb-checkpoint4-cibas
```

Topic:

```text
orders
```

Subscription:

```text
orders-subscription
```

Fila utilizada para falhas:

```text
failed-orders
```

## Storage Account

```text
stcheckpoint4cibas2026
```

Tabela utilizada para controle dos pedidos:

```text
Orders
```

## Application Insights

```text
func-checkpoint4-cibas2026
```

O Application Insights é utilizado para coletar:

* requests;
* traces;
* exceptions;
* duração das Functions;
* status de sucesso/falha;
* dimensões customizadas;
* eventos relacionados ao pedido.

---

# 4. Estrutura das Functions

As principais Functions do projeto são:

```text
check_idempotency
finish_order
order_orchestrator
process_order
process_order_activity
register_failure
register_order
validate_order
```

## `process_order`

É acionada quando uma mensagem chega ao tópico `orders` do Azure Service Bus.

Responsabilidades:

1. receber a mensagem;
2. converter o conteúdo para JSON;
3. identificar o `order_id`;
4. gerar o `instance_id`;
5. iniciar a Durable Orchestration.

Exemplo:

```text
order_id = CHK4-004

instance_id = order-CHK4-004
```

---

# 5. Durable Orchestrator

A Function:

```text
order_orchestrator
```

coordena todo o processamento do pedido.

A sequência implementada é:

```text
validate_order
        ↓
check_idempotency
        ↓
register_order
        ↓
process_order_activity
        ↓
finish_order
```

As Activities são executadas utilizando retry do Durable Functions.

Configuração utilizada:

```python
df.RetryOptions(
    first_retry_interval_in_milliseconds=5000,
    max_number_of_attempts=3
)
```

Isso permite repetir Activities em situações de falhas transitórias.

---

# 6. Validação do pedido

A Activity:

```text
validate_order
```

valida os dados recebidos.

São verificadas informações como:

* `order_id`;
* `customer`;
* `product`;
* `quantity`.

Exemplo de pedido válido:

```json
{
  "order_id": "CHK4-004",
  "customer": "cibas",
  "product": "Notebook",
  "quantity": 1
}
```

---

# 7. Idempotência

A Activity:

```text
check_idempotency
```

consulta a tabela:

```text
Orders
```

utilizando:

```text
PartitionKey = orders
RowKey = order_id
```

O objetivo é evitar que um pedido já concluído seja processado novamente.

Quando o pedido já foi concluído, o fluxo pode retornar:

```text
ALREADY_PROCESSED
```

Essa estratégia evita processamento duplicado.

---

# 8. Registro do pedido

A Activity:

```text
register_order
```

registra o pedido no Azure Table Storage.

Durante o processamento inicial, o pedido recebe:

```text
status = PROCESSING
```

Após a conclusão:

```text
status = COMPLETED
```

Em caso de erro:

```text
status = FAILED
```

---

# 9. Processamento

A Activity:

```text
process_order_activity
```

representa o processamento efetivo do pedido.

Ela também possui logging estruturado para permitir o acompanhamento da execução pelo Application Insights.

Para testes de retry, existe uma condição controlada de falha utilizando um `order_id` específico.

---

# 10. Finalização

A Activity:

```text
finish_order
```

atualiza o pedido no Table Storage para:

```text
COMPLETED
```

Essa etapa representa a conclusão bem-sucedida do processamento.

---

# 11. Tratamento de falhas

Quando uma Activity falha após as tentativas configuradas, o Orchestrator direciona o fluxo para:

```text
register_failure
```

Essa Activity:

1. registra o pedido como `FAILED`;
2. registra informações do erro;
3. envia o pedido para a fila:

```text
failed-orders
```

Isso permite que falhas sejam identificadas e tratadas posteriormente.

---

# 12. Logging estruturado

Foi implementado logging estruturado utilizando `custom_dimensions` do Application Insights.

Exemplo:

```python
logging.info(
    "Pedido recebido do Service Bus",
    extra={
        "custom_dimensions": {
            "event": "order_received",
            "order_id": str(order_id),
            "instance_id": instance_id,
            "customer": str(order.get("customer")),
            "product": str(order.get("product")),
            "quantity": str(order.get("quantity")),
            "status": "RECEIVED"
        }
    }
)
```

As principais dimensões utilizadas são:

```text
event
order_id
instance_id
activity
status
duration_ms
idempotent
```

Isso permite consultar os eventos de maneira estruturada no Application Insights.

---

# 13. Application Insights

O Application Insights foi utilizado como principal ferramenta de observabilidade.

As informações podem ser consultadas através de:

```text
Azure Portal
    ↓
Function App
    ↓
Application Insights
    ↓
Logs
```

Também é possível acessar o recurso de Application Insights diretamente pelo Azure Portal.

---

# 14. Query para acompanhar os pedidos

Uma das consultas utilizadas foi:

```kusto
traces
| where timestamp > ago(30m)
| where tostring(customDimensions.order_id) == "CHK4-004"
   or message contains "CHK4-004"
| project timestamp, message, customDimensions
| order by timestamp asc
```

Essa consulta permite acompanhar os eventos relacionados a um pedido específico.

---

# 15. Query para medir as Functions

Para analisar duração e sucesso das Functions:

```kusto
requests
| where timestamp > ago(30m)
| where name in (
    "validate_order",
    "check_idempotency",
    "register_order",
    "process_order_activity",
    "finish_order",
    "register_failure",
    "order_orchestrator",
    "process_order"
)
| project timestamp, name, resultCode, success, duration, operation_Id
| order by timestamp asc
```

Os campos utilizados são:

```text
timestamp
name
resultCode
success
duration
operation_Id
```

---

# 16. Query para identificar exceções

```kusto
exceptions
| where timestamp > ago(30m)
| project
    timestamp,
    type,
    outerMessage,
    innermostMessage,
    operation_Id
| order by timestamp asc
```

Essa consulta permite identificar erros ocorridos durante o processamento.

---

# 17. Evidência de execução — CHK4-004

Foi realizado um teste utilizando o pedido:

```text
CHK4-004
```

Payload:

```json
{
  "order_id": "CHK4-004",
  "customer": "cibas",
  "product": "Notebook",
  "quantity": 1
}
```

O Application Insights registrou a execução das principais etapas.

Resultados observados:

| Function                 | Resultado |  Duração |
| ------------------------ | --------- | -------: |
| `validate_order`         | SUCCESS   |  4,23 ms |
| `check_idempotency`      | SUCCESS   | 43,41 ms |
| `register_order`         | SUCCESS   | 52,21 ms |
| `process_order_activity` | SUCCESS   |  5,12 ms |
| `finish_order`           | SUCCESS   | 48,65 ms |

Todas apresentaram:

```text
resultCode = 0
success = True
```

Isso comprova a execução completa do pipeline para o pedido testado.

---

# 18. Análise de performance

Com base nos dados coletados no Application Insights, foi possível identificar que as maiores durações do fluxo estão concentradas nas operações relacionadas ao armazenamento.

No teste `CHK4-004`, destacaram-se:

```text
check_idempotency       43,41 ms
register_order          52,21 ms
finish_order            48,65 ms
```

Enquanto as etapas de processamento lógico apresentaram tempos menores:

```text
validate_order           4,23 ms
process_order_activity   5,12 ms
```

Isso indica que as operações de persistência e consulta ao Storage representam uma parcela relevante da latência observada.

---

# 19. Otimização técnica 1 — Redução de operações de Storage

Atualmente o pipeline realiza operações separadas para:

```text
check_idempotency
register_order
finish_order
```

Uma possível otimização é reduzir chamadas desnecessárias ao Storage ou agrupar operações quando a regra de negócio permitir.

### Benefício esperado

* menor latência;
* menor quantidade de operações;
* redução potencial de custo;
* menor dependência de chamadas externas.

A alteração deve preservar a idempotência e a consistência do processamento.

---

# 20. Otimização técnica 2 — Estratégia de Retry

O pipeline utiliza:

```text
5 segundos
até 3 tentativas
```

Essa estratégia é adequada para falhas transitórias, mas erros permanentes não devem necessariamente ser repetidos.

Uma melhoria seria diferenciar:

```text
Erro transitório
    → retry

Erro permanente/de validação
    → falha imediata
```

Também pode ser utilizada uma estratégia de backoff progressivo.

### Benefício esperado

* menor tempo desperdiçado;
* menor quantidade de execuções;
* redução de custo;
* menor carga sobre os serviços dependentes.

---

# 21. Otimização técnica 3 — Dashboards e alertas

Os dados coletados podem ser utilizados para criar indicadores de:

* taxa de sucesso;
* taxa de falha;
* duração média;
* p95 de duração;
* quantidade de retries;
* pedidos `FAILED`;
* pedidos `ALREADY_PROCESSED`.

### Benefício esperado

A equipe consegue identificar rapidamente:

```text
degradação de performance
        ↓
aumento de erros
        ↓
aumento de retries
        ↓
possível problema operacional
```

Isso melhora a capacidade de diagnóstico e reduz o tempo necessário para identificar problemas.

---

# 22. Análise de custos

A arquitetura utiliza serviços serverless e serviços gerenciados do Azure.

Os principais componentes que podem gerar consumo são:

```text
Azure Functions
Azure Service Bus
Azure Storage
Application Insights / Azure Monitor
```

O custo pode aumentar conforme:

* quantidade de mensagens;
* número de execuções;
* quantidade de operações no Storage;
* quantidade de telemetria ingerida;
* quantidade de retries;
* retenção de logs.

Uma otimização importante é evitar logging excessivo em produção.

Logs devem conter as informações necessárias para diagnóstico sem gerar volume desnecessário de telemetria.

---

# 23. Teste de Retry

Para validar o mecanismo de retry, deve ser enviado um pedido utilizando a condição de falha controlada implementada na Activity:

```text
process_order_activity
```

O comportamento esperado é:

```text
process_order_activity
        ↓
      erro
        ↓
      retry
        ↓
      erro
        ↓
      retry
        ↓
      erro
        ↓
register_failure
        ↓
FAILED
        ↓
failed-orders
```

A execução deve ser comprovada através do Application Insights.

---

# 24. Teste de idempotência

Para validar a idempotência, deve ser enviado novamente um pedido cujo `order_id` já tenha sido processado.

Exemplo:

```text
CHK4-004
```

O comportamento esperado é:

```text
check_idempotency
        ↓
pedido encontrado
        ↓
status = COMPLETED
        ↓
already_processed = true
        ↓
ALREADY_PROCESSED
```

O pedido não deve ser processado novamente.

---


# 25. Conclusão

O Checkpoint 4 evoluiu o pipeline serverless dos checkpoints anteriores adicionando uma camada de observabilidade baseada em **Azure Monitor e Application Insights**.

A solução permite acompanhar:

```text
entrada do pedido
       ↓
orquestração
       ↓
validação
       ↓
idempotência
       ↓
persistência
       ↓
processamento
       ↓
finalização
       ↓
resultado
```

Além disso, a instrumentação permite identificar duração, sucesso, falhas, retries e eventos relacionados a cada pedido.

O teste `CHK4-004` demonstrou a execução bem-sucedida das principais etapas do pipeline, servindo como evidência da integração entre **Service Bus, Durable Functions, Table Storage e Application Insights**.

As otimizações propostas concentram-se na redução de operações de Storage, melhoria da estratégia de retry e evolução da observabilidade com métricas, dashboards e alertas.

---

## Tecnologias utilizadas

* Python 3.11
* Azure Functions
* Azure Durable Functions
* Azure Service Bus
* Azure Storage / Table Storage
* Azure Application Insights
* Azure Monitor
* Kusto Query Language (KQL)
* PowerShell
