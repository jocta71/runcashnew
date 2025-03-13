#!/bin/bash

# Script para iniciar o sistema RunCash com o simulador para testes

echo "=== RunCash - Iniciando com Simulador ==="
echo "Este script inicia o sistema com dados simulados para testes"

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "Python 3 não encontrado! Por favor, instale o Python 3."
    exit 1
fi

# Verificar se as dependências estão instaladas
if ! python3 -c "import flask" &> /dev/null; then
    echo "Dependências não encontradas. Instalando..."
    pip3 install -r requirements.txt
fi

# Verificar se .env existe, caso contrário, criar a partir do exemplo
if [ ! -f .env ]; then
    echo "Arquivo .env não encontrado. Criando a partir de .env.example..."
    cp .env.example .env
    echo "Arquivo .env criado com configurações padrão."
fi

echo "Iniciando o sistema com simulador de dados..."
echo "O simulador irá gerar dados aleatórios para as roletas."
echo "Pressione Ctrl+C para encerrar."
echo ""

# Iniciar o sistema com simulador
cd backend/scraper
python3 run.py --mongodb --simulate 