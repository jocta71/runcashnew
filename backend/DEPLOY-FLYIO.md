# Deploy do Backend no Fly.io

Este guia explica como fazer o deploy do backend do RunCash no Fly.io.

## Pré-requisitos

1. [Conta no Fly.io](https://fly.io/app/sign-up)
2. [Flyctl CLI](https://fly.io/docs/hands-on/install-flyctl/) instalado
3. Git instalado
4. Linha de comando (terminal)

## Passo 1: Configurar o Fly.io

1. Instale o CLI do Fly.io seguindo as instruções em: https://fly.io/docs/hands-on/install-flyctl/

2. Faça login na sua conta Fly.io:
   ```
   flyctl auth login
   ```

## Passo 2: Preparar o projeto para deploy

1. Certifique-se de estar no diretório `backend`:
   ```
   cd backend
   ```

2. Verifique se os seguintes arquivos estão presentes:
   - `Dockerfile`
   - `fly.toml`
   - `requirements.txt`
   - `scraper/app.py` (com as modificações necessárias)

## Passo 3: Lançar a aplicação no Fly.io

1. Execute o comando:
   ```
   flyctl launch
   ```

2. Quando solicitado, responda:
   - Escolha um nome para sua aplicação (ou deixe o padrão "runcash-backend")
   - Escolha a região "gru" (São Paulo) ou a mais próxima de você
   - Selecione "N" quando perguntar se quer configurar PostgreSQL ou Redis
   - Selecione "N" quando perguntar se quer fazer deploy agora (vamos configurar as variáveis de ambiente primeiro)

## Passo 4: Configurar variáveis de ambiente

1. Configure as variáveis de ambiente necessárias:
   ```
   flyctl secrets set SUPABASE_URL=https://evzqzghxuttctbxgohpx.supabase.co
   flyctl secrets set SUPABASE_KEY=sua_chave_do_supabase
   flyctl secrets set CASINO_URL="https://es.888casino.com/live-casino/#filters=live-roulette"
   flyctl secrets set SCRAPE_INTERVAL_MINUTES=5
   flyctl secrets set MAX_CICLOS=0
   flyctl secrets set ALLOWED_ROULETTES="*"
   ```

## Passo 5: Fazer o deploy

1. Execute o comando:
   ```
   flyctl deploy
   ```

2. Aguarde o processo de build e deploy concluir. Pode levar alguns minutos.

## Passo 6: Verificar o status da aplicação

1. Veja informações sobre sua aplicação:
   ```
   flyctl status
   ```

2. Para ver os logs da aplicação:
   ```
   flyctl logs
   ```

## Passo 7: Obter a URL para o frontend

A URL do seu backend será algo como:
```
https://runcash-backend.fly.dev
```

Use esta URL no frontend, adicionando o caminho `/events`:
```
https://runcash-backend.fly.dev/events
```

Configure esta URL completa no projeto Vercel, na variável de ambiente `VITE_SSE_SERVER_URL`.

## Comandos úteis

- Para ver os logs em tempo real:
  ```
  flyctl logs -a runcash-backend
  ```

- Para reiniciar a aplicação:
  ```
  flyctl restart -a runcash-backend
  ```

- Para abrir o console da aplicação:
  ```
  flyctl ssh console -a runcash-backend
  ```

## Solução de problemas

Se encontrar problemas durante o deploy:

1. Verifique os logs:
   ```
   flyctl logs
   ```

2. Verifique se todas as variáveis de ambiente estão configuradas:
   ```
   flyctl secrets list
   ```

3. Verifique se o Dockerfile está correto e contém todas as dependências necessárias.

4. Se precisar, você pode destruir a aplicação e recomeçar:
   ```
   flyctl destroy runcash-backend
   ``` 