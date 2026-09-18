# Checkpoint 5 — CI/CD e Observabilidade com Azure Functions

## 1. Objetivo

Este checkpoint implementa um pipeline de **CI/CD utilizando GitHub Actions** para automatizar a validação e o deploy de uma aplicação **Azure Functions**.

A solução utiliza:

* GitHub Actions
* Azure Functions
* Azure Functions Flex Consumption
* Python 3.11
* Azure Durable Functions
* Azure Service Bus
* Azure Table Storage
* Application Insights
* Microsoft Entra ID / OIDC
* GitHub Actions Secrets

O objetivo é permitir que alterações realizadas na branch `main` sejam automaticamente validadas e publicadas no Azure.

---

## 2. Arquitetura

O fluxo implementado é baseado no seguinte modelo:

```text
                    GitHub
                       |
                       | Push na branch main
                       v
              GitHub Actions
                       |
              +--------+--------+
              |                 |
              v                 v
        Setup Python       Validação/Testes
              |                 |
              +--------+--------+
                       |
                       v
                Azure Login
                    OIDC
                       |
                       v
              Azure Functions
              Flex Consumption
                       |
                       v
             Durable Functions
                       |
          +------------+-------------+
          |            |             |
          v            v             v
    Service Bus   Table Storage   App Insights
```

---

## 3. Componentes Azure

### Function App

A aplicação utiliza a Function App:

```text
func-checkpoint4-cibas2026
```

A mesma Function App utilizada no Checkpoint 4 é reutilizada neste checkpoint.

O plano utilizado é:

```text
Flex Consumption
```

Runtime:

```text
Python 3.11
```

Resource Group:

```text
VisualStudioOnline-FBDD2D6D4E494DF1BED16F161CD7EC5B
```

---

## 4. GitHub Actions

O workflow está localizado em:

```text
.github/workflows/azure-function-deploy.yml
```

O workflow é executado automaticamente quando ocorre um `push` na branch:

```text
main
```

Também é possível executá-lo manualmente através de:

```yaml
workflow_dispatch
```

### Etapas do pipeline

O pipeline executa as seguintes etapas:

1. Checkout do código
2. Configuração do Python 3.11
3. Instalação das dependências
4. Validação da sintaxe Python
5. Execução dos testes
6. Login no Azure utilizando OIDC
7. Deploy da Azure Function

---

## 5. Configuração do Python

O pipeline utiliza:

```yaml
PYTHON_VERSION: "3.11"
```

O código da aplicação está localizado em:

```text
cloud-serverless-checkpoint5
```

Por isso, o deploy utiliza esse diretório como pacote da Function:

```yaml
package: ${{ env.APP_PATH }}
```

O diretório contém o arquivo obrigatório:

```text
host.json
```

---

## 6. Dependências

As dependências da aplicação estão definidas em:

```text
requirements.txt
```

Atualmente:

```text
azure-functions
azure-functions-durable
azure-servicebus
azure-data-tables
azure-core
```

A biblioteca:

```text
azure-functions-durable
```

fornece o suporte utilizado pelo código para:

```python
import azure.durable_functions as df
```

---

## 7. Durable Functions

A aplicação utiliza o modelo Python v2 das Azure Functions.

O ponto principal da aplicação está em:

```text
function_app.py
```

A aplicação utiliza:

```python
app = df.DFApp()
```

O fluxo principal é iniciado através de uma mensagem recebida pelo Azure Service Bus.

### Trigger do Service Bus

A Function possui um trigger associado ao tópico:

```text
orders
```

e à subscription:

```text
orders-subscription
```

A conexão é obtida através da configuração:

```text
SERVICE_BUS_CONNECTION
```

---

## 8. Orquestração

A orquestração principal é:

```text
order_orchestrator
```

O fluxo executado é:

```text
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
       +--> finish_order
```

Em caso de falha definitiva:

```text
order_orchestrator
       |
       v
register_failure
       |
       +--> Azure Table Storage
       |
       +--> Service Bus
              |
              v
        failed-orders
```

---

## 9. Idempotência

A aplicação utiliza Azure Table Storage para controlar o processamento dos pedidos.

Tabela:

```text
Orders
```

Partition Key:

```text
orders
```

Row Key:

```text
order_id
```

O fluxo verifica se o pedido já foi processado antes de iniciar uma nova execução.

Estados utilizados:

```text
NEW
PROCESSING
COMPLETED
FAILED
```

---

## 10. Retry

A orquestração utiliza o mecanismo de retry do Durable Functions.

Configuração:

```python
retry_options = df.RetryOptions(
    first_retry_interval_in_milliseconds=5000,
    max_number_of_attempts=3
)
```

Portanto:

```text
Intervalo inicial: 5 segundos
Máximo de tentativas: 3
```

Existe também um teste controlado de falha utilizando:

```text
order_id = 9999
```

Nesse caso, a Activity:

```text
process_order_activity
```

gera uma exceção propositalmente para permitir a validação do mecanismo de retry.

---

## 11. Tratamento de falhas

Quando ocorre uma falha definitiva, a aplicação executa:

```text
register_failure
```

Essa Activity:

1. Registra o pedido como `FAILED` no Table Storage.
2. Registra informações do erro.
3. Envia uma mensagem para a fila:

```text
failed-orders
```

A mensagem contém informações como:

```json
{
  "order_id": "9999",
  "status": "FAILED",
  "error": "Erro proposital para testar retry"
}
```

---

## 12. Application Insights

A aplicação utiliza logs estruturados para facilitar a observabilidade.

Os eventos são registrados através de `custom_dimensions`.

Exemplos de eventos:

```text
order_received
orchestration_started
order_validation_started
order_validation_completed
idempotency_check_started
order_registration_started
order_processing_started
order_processing_completed
order_completed
order_failed
failed_order_queued
```

As dimensões podem conter informações como:

```text
order_id
instance_id
activity
status
duration_ms
error_type
error
```

Essas informações podem ser consultadas no Application Insights utilizando KQL.

---

## 13. Autenticação GitHub → Azure

O pipeline utiliza **OpenID Connect (OIDC)** para autenticar o GitHub Actions no Azure.

Não é utilizado um client secret tradicional para o login.

O workflow utiliza:

```yaml
permissions:
  id-token: write
  contents: read
```

E realiza o login através de:

```yaml
uses: azure/login@v2
```

com:

```yaml
client-id: ${{ secrets.AZURE_CLIENT_ID }}
tenant-id: ${{ secrets.AZURE_TENANT_ID }}
subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
```

---

## 14. GitHub Secrets

Os seguintes secrets são utilizados pelo workflow:

```text
AZURE_CLIENT_ID
AZURE_SUBSCRIPTION_ID
AZURE_TENANT_ID
```

Esses valores não ficam armazenados diretamente no código-fonte.

---

## 15. Federated Credential

Para permitir o login via OIDC, foi criada uma credencial federada no Microsoft Entra ID.

A credencial associa o repositório GitHub ao Service Principal utilizado pelo pipeline.

O fluxo é:

```text
GitHub Actions
      |
      | OIDC Token
      v
Microsoft Entra ID
      |
      | Federated Credential
      v
Service Principal
      |
      v
Azure
```

Essa configuração elimina a necessidade de armazenar um segredo de longa duração no GitHub Actions.

---

## 16. Validação local

Antes do deploy, o projeto pode ser validado localmente.

Criar ambiente virtual:

```powershell
python -m venv .venv
```

Ativar:

```powershell
.\.venv\Scripts\Activate.ps1
```

Instalar dependências:

```powershell
python -m pip install -r requirements.txt
```

Validar o carregamento da aplicação:

```powershell
python -c "import function_app; print('IMPORT_OK')"
```

Validar a sintaxe:

```powershell
python -m compileall -q .
```

---

## 17. Pipeline de CI/CD

O processo completo é:

```text
Alteração no código
        |
        v
git add
        |
        v
git commit
        |
        v
git push origin main
        |
        v
GitHub Actions
        |
        +--> Checkout
        |
        +--> Python 3.11
        |
        +--> pip install
        |
        +--> compileall
        |
        +--> pytest
        |
        +--> Azure Login / OIDC
        |
        +--> Azure Functions Deploy
        |
        v
Function App atualizada
```

---

## 18. Comandos de validação

### Verificar o workflow

```powershell
gh workflow list
```

### Verificar execuções

```powershell
gh run list --workflow "Checkpoint 5 - Azure Function CI/CD" --limit 5
```

### Verificar detalhes da última execução

```powershell
gh run view <RUN_ID>
```

### Verificar as Functions publicadas

```powershell
az functionapp function list `
  --name func-checkpoint4-cibas2026 `
  --resource-group VisualStudioOnline-FBDD2D6D4E494DF1BED16F161CD7EC5B `
  --query "[].name" `
  -o table
```

### Verificar o runtime Flex Consumption

```powershell
az resource show `
  --resource-group VisualStudioOnline-FBDD2D6D4E494DF1BED16F161CD7EC5B `
  --name func-checkpoint4-cibas2026 `
  --resource-type Microsoft.Web/sites `
  --api-version 2024-04-01 `
  --query "properties.functionAppConfig.runtime" `
  -o json
```

Resultado esperado:

```json
{
  "name": "python",
  "version": "3.11"
}
```

---

## 19. Evidências

As evidências do checkpoint estão armazenadas em:

```text
evidencias/
```

Exemplos:

```text
checkpoint-5-1.png
checkpoint-5-2.png
```

Essas evidências documentam a execução e validação do Checkpoint 5.

---

## 20. Estrutura do projeto

```text
cloud-serverless-checkpoint5/
│
├── .funcignore
├── .gitignore
├── README.md
├── activities.py
├── function_app.py
├── host.json
├── orchestrator.py
├── requirements.txt
│
├── evidencias/
│   ├── checkpoint-5-1.png
│   └── checkpoint-5-2.png
│
└── src/
    └── functions/
        └── HelloWorld.js
```

---

## 21. Resultado esperado

Ao final do checkpoint, o processo de entrega deve permitir:

* validar automaticamente o código Python;
* instalar automaticamente as dependências;
* executar testes automatizados quando disponíveis;
* autenticar no Azure sem armazenar client secret;
* realizar o deploy automático da Azure Function;
* executar Durable Functions;
* processar mensagens do Service Bus;
* controlar idempotência utilizando Table Storage;
* realizar retry de Activities;
* registrar falhas;
* enviar pedidos com falha para `failed-orders`;
* gerar logs estruturados para observabilidade no Application Insights.

---

## 22. Conclusão

O Checkpoint 5 demonstra a integração entre **desenvolvimento, automação de entrega, autenticação segura e serviços serverless do Azure**.

O uso de GitHub Actions permite automatizar o ciclo de entrega da aplicação, enquanto Azure Functions, Durable Functions, Service Bus, Table Storage e Application Insights formam a infraestrutura necessária para processamento assíncrono, controle de estado, retry, tratamento de falhas e observabilidade.
