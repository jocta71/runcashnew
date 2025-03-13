# Integração Backend-Frontend para RunCash

Este guia contém instruções para conectar o backend MongoDB do RunCash ao frontend hospedado no Vercel.

## Visão Geral

O sistema está dividido em duas partes:

1. **Backend**: Sistema Python que faz a captura de dados das roletas e armazena no MongoDB
2. **Frontend**: Aplicação React hospedada no Vercel que exibe os dados das roletas em tempo real

A comunicação entre backend e frontend é realizada através de:
- API REST para dados estáticos e históricos
- Server-Sent Events (SSE) para atualizações em tempo real

## Configuração do Backend

### 1. Certifique-se de que o backend esteja acessível publicamente

Para que o frontend no Vercel possa acessar o backend, ele precisa estar acessível na internet. Você tem algumas opções:

- **Hospedagem em serviço de nuvem** (recomendado):
  - [Render](https://render.com/) (tem plano gratuito)
  - [Heroku](https://www.heroku.com/)
  - [Railway](https://railway.app/)
  - [DigitalOcean](https://www.digitalocean.com/)

- **Exposição temporária para testes**:
  - [ngrok](https://ngrok.com/): `ngrok http 5000`
  - [localtunnel](https://localtunnel.github.io/www/): `lt --port 5000`

### 2. Definindo variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto backend:

```
MONGODB_URI=sua_string_de_conexao_mongodb
MONGODB_DATABASE=nome_do_seu_banco
ALLOWED_ORIGINS=https://runcashnew-frontend-nu.vercel.app,http://localhost:3000
PORT=5000
HOST=0.0.0.0
```

### 3. Iniciando o backend

Para iniciar o backend com suporte à conexão com o frontend:

```bash
cd backend/scraper
python run.py --mongodb --host 0.0.0.0 --port 5000
```

O sistema vai mostrar na saída do terminal a URL da API.

## Conectando o Frontend

### 1. Atualização da URL da API no Frontend

No seu projeto frontend, localize o arquivo onde as chamadas de API são feitas e atualize a URL base:

```javascript
// Substitua:
const API_URL = 'http://localhost:5000';

// Por:
const API_URL = 'https://seu-backend.example.com'; // URL da sua hospedagem
```

### 2. Implementação em React

O arquivo `frontend-example/RouletteDisplay.jsx` mostra um exemplo de como consumir os dados do backend. As principais partes são:

- Carregamento inicial via API REST
- Conexão SSE para atualizações em tempo real
- Lógica de atualização automática da interface

Você pode integrar este componente ao seu projeto React existente ou usar como referência para adaptar sua implementação atual.

### 3. CORS e Segurança

O backend já está configurado para permitir solicitações do domínio Vercel especificado na variável de ambiente ALLOWED_ORIGINS. Se você precisar adicionar outros domínios, atualize essa variável.

## Testando a Integração

1. Inicie o backend
2. Verifique se a API está respondendo acessando `http://seu-backend:5000/api/status`
3. No frontend, verifique o console do navegador para confirmar a conexão SSE estabelecida
4. As roletas e seus números devem aparecer na interface e atualizar em tempo real

## Endpoints Disponíveis

### API REST

- `GET /api/status`: Verifica se a API está online
- `GET /api/roletas`: Lista todas as roletas disponíveis
- `GET /api/roletas/:id`: Obtém detalhes de uma roleta específica
- `GET /api/roletas/:id/numeros`: Obtém os últimos números de uma roleta

### SSE (Server-Sent Events)

- `GET /api/events`: Estabelece uma conexão SSE para receber atualizações em tempo real

## Troubleshooting

### Problemas de CORS

Se encontrar erros de CORS no console do navegador:
1. Verifique se a URL do frontend está corretamente listada em ALLOWED_ORIGINS
2. Certifique-se de não estar usando HTTP no frontend e HTTPS no backend (ou vice-versa)
3. O back-end deve enviar os cabeçalhos CORS apropriados

### SSE não está conectando

1. Verifique se o navegador suporta EventSource (todos os navegadores modernos suportam)
2. Teste a conexão SSE usando uma ferramenta como [SSE-Client](https://www.npmjs.com/package/sse-client)
3. Verifique se há firewalls ou proxies bloqueando conexões persistentes

### Dados não estão atualizando em tempo real

1. Verifique o console do navegador para erros
2. Confirme que o EventManager está emitindo eventos para novos números
3. Verifique se a função que processa eventos no frontend está funcionando corretamente

## Recursos Adicionais

- [MDN: Using Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [React Hooks for Web Sockets](https://usehooks.com/useWebSocket/)
- [MongoDB Node.js Driver](https://docs.mongodb.com/drivers/node/) 