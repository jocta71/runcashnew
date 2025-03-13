# RunCash com MongoDB

Este guia contém instruções detalhadas para configurar e executar o sistema RunCash utilizando MongoDB como banco de dados.

## Pré-requisitos

1. **Python 3.6+** instalado
2. **MongoDB** instalado (ou acesso a um servidor MongoDB)
3. **Git** (opcional, para clonar o repositório)

## Instalação

### 1. Instalar Dependências

```bash
pip install pymongo dnspython flask flask-cors selenium webdriver-manager python-dotenv
```

### 2. Configurar MongoDB

#### Opção A: MongoDB Local
1. Instale o MongoDB seguindo as instruções em [mongodb.com/download](https://www.mongodb.com/try/download/community)
2. Inicie o servidor MongoDB (geralmente executado na porta 27017)
3. Opcional: Instale o MongoDB Compass para uma interface gráfica

#### Opção B: MongoDB Atlas (em nuvem)
1. Crie uma conta gratuita em [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Crie um cluster gratuito
3. Configure um usuário e senha
4. Obtenha a string de conexão

### 3. Configurar o Arquivo .env

Crie um arquivo `.env` na pasta `backend/scraper/` com o seguinte conteúdo:

```
# MongoDB
MONGODB_URI=mongodb://localhost:27017/runcash
MONGODB_DB_NAME=runcash
MONGODB_ENABLED=true

# Desabilitar Supabase (opcional)
SUPABASE_ENABLED=false

# Configurações gerais
PRODUCTION=false
HOST=0.0.0.0
PORT=5000

# URL do Casino (opcional)
CASINO_URL=https://www.cassinobrazil.com/
```

Se estiver usando MongoDB Atlas, substitua a linha `MONGODB_URI` pela string de conexão fornecida pelo Atlas.

## Execução

### Iniciar o Sistema Completo

Para iniciar o sistema completo usando MongoDB:

```bash
cd backend/scraper
python run.py --mongodb
```

### Iniciar em Modo de Simulação

Se você quiser simular dados sem o scraper real:

```bash
cd backend/scraper
python run.py --mongodb --simulate
```

### Iniciar Apenas o Servidor

Se você deseja apenas iniciar o servidor API/web:

```bash
cd backend/scraper
python run.py --mongodb --only-server
```

### Outras Opções

```bash
# Mostrar todas as opções disponíveis
python run.py --help

# Usar a implementação original (apenas com suporte parcial a MongoDB)
python run.py --mongodb --legacy

# Usar a nova implementação modular
python run.py --mongodb --new

# Usar a implementação integrada (padrão)
python run.py --mongodb --integrado

# Especificar host e porta
python run.py --mongodb --host 127.0.0.1 --port 8000
```

## Verificação

1. Acesse a interface web em: http://localhost:5000
2. Verifique o status do sistema em: http://localhost:5000/api/status
3. Consulte as roletas disponíveis em: http://localhost:5000/api/roletas
4. Veja eventos em tempo real em: http://localhost:5000/events

## Banco de Dados

O sistema criará automaticamente o banco de dados `runcash` no MongoDB com as seguintes coleções:

- `roletas` - Informações sobre as roletas disponíveis
- `roleta_numeros` - Histórico de números que saíram nas roletas
- `roleta_estatisticas_diarias` - Estatísticas diárias de cada roleta
- `roleta_sequencias` - Sequências de números detectadas

## Solução de Problemas

### Conexão com MongoDB

Se encontrar problemas de conexão com o MongoDB:

1. Verifique se o serviço MongoDB está em execução
2. Confirme que a URI no arquivo `.env` está correta
3. Verifique as configurações de firewall se estiver usando um servidor remoto

### Scraper

Se o scraper não estiver funcionando corretamente:

1. Verifique se o ChromeDriver está atualizado
2. Teste a URL do casino no navegador para confirmar que é acessível
3. Verifique os logs em `logs/runcash_YYYY-MM-DD.log`

### Servidor Web

Se o servidor web não iniciar:

1. Verifique se a porta 5000 está disponível
2. Confirme que todas as dependências estão instaladas
3. Verifique os logs para identificar erros específicos

## Backup e Restauração

### Backup

Para fazer backup dos dados do MongoDB:

```bash
mongodump --uri="mongodb://localhost:27017" --db=runcash --out=backup_folder
```

### Restauração

Para restaurar os dados do backup:

```bash
mongorestore --uri="mongodb://localhost:27017" --db=runcash backup_folder/runcash
```

## Informações Adicionais

- Os logs do sistema são armazenados na pasta `logs/`
- A configuração do servidor está no arquivo `.env`
- Os dados de simulação são aleatórios, mas seguem padrões semelhantes aos dados reais 