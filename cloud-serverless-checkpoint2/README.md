# Checkpoint 2 - Arquitetura Serverless Orientada a Eventos

Neste Checkpoint 2, o projeto desenvolvido no Checkpoint 1 foi evoluído de uma função serverless HTTP simples para uma arquitetura orientada a eventos (Event-Driven), utilizando o Azure Service Bus.

A função agora é acionada automaticamente sempre que uma nova mensagem é publicada no tópico `orders`. A mensagem é recebida pela subscription `orders-subscription`, e a função realiza o processamento das informações do pedido.

## Provedor Utilizado

* Azure
* Azure Functions
* Azure Service Bus
* Service Bus Topic
* Service Bus Subscription
* Python

## Como rodar localmente

### Pré-requisitos

* Python instalado (versão 3.10 ou superior)
* Azure Functions Core Tools
* Azure CLI instalado
* Git instalado
* Conta no Microsoft Azure
* Terminal de comandos aberto

### Passo a passo

1. Clone o repositório para sua máquina:

```bash
git clone https://github.com/cibascastropuc2/puc-serverless.git
```

2. Entre na pasta do projeto:

```bash
cd puc-serverless/cloud-serverless-checkpoint2
```

3. Crie e ative um ambiente virtual Python:

```bash
python -m venv .venv
```

No Windows:

```bash
.venv\Scripts\activate
```

4. Instale as dependências do projeto:

```bash
pip install -r requirements.txt
```

5. Configure a variável de ambiente `SERVICE_BUS_CONNECTION` com a connection string do Azure Service Bus.

6. Inicie a Azure Function localmente:

```bash
func start
```

7. Publique uma mensagem no tópico `orders` do Azure Service Bus.

8. A mensagem será recebida pela subscription `orders-subscription` e processada pela função `process_order`.

## Funcionamento

A função recebe a mensagem do Azure Service Bus, converte o conteúdo para JSON e registra nos logs as informações do pedido, como:

* Order ID
* Cliente
* Produto
* Quantidade

Após o processamento, a função registra a mensagem:

```text
Pedido processado com sucesso.
```

## Segurança

A aplicação utiliza um tópico privado do Azure Service Bus para acionar a função, não sendo necessário expor uma URL HTTP pública.

A connection string do Azure Service Bus não deve ser publicada no GitHub.

Não devem ser adicionados ao repositório:

* Connection Strings
* Chaves de acesso
* Senhas
* Tokens
* Arquivos `.json` contendo credenciais
* Arquivos `.env` contendo informações sensíveis

As informações de conexão devem ser configuradas localmente e mantidas fora do controle de versão.

## Arquitetura

O fluxo da aplicação é:

```text
Publicação de pedido
        ↓
Azure Service Bus Topic
        ↓
orders
        ↓
orders-subscription
        ↓
Azure Function
        ↓
process_order
        ↓
Processamento do pedido
```
