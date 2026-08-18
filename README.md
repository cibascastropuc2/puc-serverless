# Checkpoint 1 - Funcao Serverless na Nuvem

Este projeto contem uma funcao serverless simples que responde a requisicoes HTTP e foi implantada em ambiente de nuvem.

## Provedor Utilizado
* Azure

## Como rodar localmente

### Pre-requisitos
* Node.js instalado (versao 18 ou superior)
* Azure Functions Core Tools
* Git
  
### Passo a passo
1. Clone o repositorio para sua maquina:
   git clone https://github.com/seu-usuario/cloud-serverless-checkpoint1.git

2. Entre na pasta do projeto:
   cd cloud-serverless-checkpoint1

3. Instale as dependencias do projeto:
   npm install

4. Rode o servidor de testes local:
   npm start

5. Executar a Azure Function localmente
  func start

6. Testar a função
   Abra o navegador e acesse:
   http://localhost:7071/api/HelloWorld
   
7. Resultado:
   Olá! Minha primeira função serverless está funcionando!

8. Acesso à função publicada na Azure
   A aplicação também foi publicada como uma Azure Function e possui um endpoint HTTP público para avaliação.
   Por questões de segurança, conforme solicitado no enunciado do Checkpoint 1, a URL pública da função não é disponibilizada    neste README, pois este repositório é público.
   O endpoint publicado será disponibilizado ao professor separadamente para realização do teste em ambiente Azure.
   
