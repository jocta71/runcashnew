#!/bin/bash

# Script para iniciar o servidor WebSocket

echo "Iniciando servidor WebSocket para comunicação em tempo real..."

# Verificar se Node.js está instalado
if ! command -v node &> /dev/null; then
    echo "Node.js não encontrado. Por favor, instale o Node.js."
    exit 1
fi

# Carregar variáveis de ambiente, se existirem
if [ -f .env ]; then
    echo "Carregando variáveis de ambiente de .env..."
    export $(grep -v '^#' .env | xargs)
fi

# Definir variáveis padrão
export PORT=${PORT:-5001}
export MONGODB_URI=${MONGODB_URI:-mongodb://localhost:27017/runcash}
export MONGODB_DB_NAME=${MONGODB_DB_NAME:-runcash}
export ALLOWED_ORIGINS=${ALLOWED_ORIGINS:-https://runcashnew-frontend-nu.vercel.app,http://localhost:3000}

echo "Configuração:"
echo "* Porta: $PORT"
echo "* MongoDB URI: $MONGODB_URI"
echo "* MongoDB Database: $MONGODB_DB_NAME"
echo "* CORS Origins: $ALLOWED_ORIGINS"

# Instalar dependências se necessário
if [ ! -d "node_modules" ]; then
    echo "Instalando dependências..."
    npm install socket.io express cors mongodb dotenv
fi

# Executar servidor
echo "Iniciando servidor WebSocket..."
node websocket_server.js 