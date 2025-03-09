# Roulette Scraper para RunCash

Este é um scraper para coletar números de roletas do site 888casino e enviar para o Supabase.

## Funcionalidades

- Extrai números de roletas em tempo real do site 888casino
- Filtra roletas por ID permitido
- Armazena histórico de até 20 números para cada roleta
- Integração com Supabase para armazenamento dos dados
- Preparado para deploy no Heroku

## Configuração

1. Crie um arquivo `.env` baseado no `.env.example`:
```
cp .env.example .env
```

2. Preencha as variáveis de ambiente no arquivo `.env`:
- `SUPABASE_URL`: URL do seu projeto Supabase
- `SUPABASE_KEY`: Chave de serviço (service key) do Supabase
- `ALLOWED_ROULETTES`: Lista de IDs de roletas permitidas, separadas por vírgula (deixe vazio para permitir todas)
- `SCRAPE_INTERVAL_MINUTES`: Intervalo em minutos entre cada execução do scraper

## Estrutura de Dados no Supabase

Os dados são armazenados na tabela `roletas` com a seguinte estrutura:
```json
{
  "id": "historico",
  "data": {
    "Roleta VIP": {
      "numeros": [23, 15, 7, ...],  // Até 20 números mais recentes
      "ultima_atualizacao": "2023-10-10 14:30:45",
      "estrategia": {}  // Dados adicionais do analisador
    },
    "Roleta Express": {
      // Similar ao acima
    }
  },
  "updated_at": "2023-10-10T14:30:45.000Z"
}
```

## Criação da Tabela no Supabase

1. Acesse o dashboard do Supabase
2. Vá para a seção "Table Editor"
3. Clique em "Create a new table"
4. Defina o nome da tabela como `roletas`
5. Adicione as seguintes colunas:
   - `id` (tipo: text, primary key)
   - `data` (tipo: jsonb, not null)
   - `updated_at` (tipo: timestamp with time zone, default: now())
6. Clique em "Save"

Ou execute o seguinte SQL:
```sql
CREATE TABLE roletas (
    id TEXT PRIMARY KEY,
    data JSONB NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Criar um registro inicial
INSERT INTO roletas (id, data) VALUES ('historico', '{}');
```

## Deploy no Heroku

1. Crie uma aplicação no Heroku:
```
heroku create runcash-scraper
```

2. Adicione os buildpacks necessários:
```
heroku buildpacks:add heroku/python
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-google-chrome
heroku buildpacks:add https://github.com/heroku/heroku-buildpack-chromedriver
```

3. Configure as variáveis de ambiente:
```
heroku config:set SUPABASE_URL=seu_url
heroku config:set SUPABASE_KEY=sua_chave
heroku config:set ALLOWED_ROULETTES=id1,id2,id3
heroku config:set SCRAPE_INTERVAL_MINUTES=5
heroku config:set GOOGLE_CHROME_BIN=/app/.apt/usr/bin/google-chrome
heroku config:set CHROMEDRIVER_PATH=/app/.chromedriver/bin/chromedriver
```

4. Deploy da aplicação:
```
git push heroku main
```

## Execução Local

1. Instale as dependências:
```
pip install -r requirements.txt
```

2. Execute o setup para verificar a conexão com o Supabase:
```
python setup_supabase.py
```

3. Execute o scraper:
```
python app.py
```

## Solução de Problemas

### Erro com o ChromeDriver
Se você encontrar erros relacionados ao ChromeDriver, verifique:
1. Se o Chrome está instalado no sistema
2. Se a versão do ChromeDriver é compatível com a versão do Chrome
3. Tente usar o método direto de inicialização do driver (já implementado como fallback)

### Erro de Conexão com o Supabase
1. Verifique se as credenciais estão corretas no arquivo `.env`
2. Confirme se a tabela `roletas` existe no Supabase
3. Verifique se a versão do cliente Supabase é compatível (recomendado: 2.3.0)

## Manutenção

O scraper foi projetado para ser resiliente, mas é recomendado:
1. Monitorar os logs do Heroku regularmente
2. Verificar se os dados estão sendo atualizados no Supabase
3. Atualizar as dependências periodicamente para evitar problemas de segurança
