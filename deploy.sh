#!/bin/bash

# Script de deployment para o RunCash API

echo "=== RunCash API - Script de Deployment ==="
echo "Este script ajuda a preparar e iniciar o backend do RunCash"

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo "Python 3 não encontrado! Por favor, instale o Python 3."
    exit 1
fi

# Verificar se pip está instalado
if ! command -v pip3 &> /dev/null; then
    echo "pip3 não encontrado! Por favor, instale o pip."
    exit 1
fi

# Instalar dependências
echo "Instalando dependências..."
pip3 install -r requirements.txt

# Verificar se .env existe, caso contrário, criar a partir do exemplo
if [ ! -f .env ]; then
    echo "Arquivo .env não encontrado. Criando a partir de .env.example..."
    cp .env.example .env
    echo "Por favor, edite o arquivo .env com suas configurações antes de continuar."
    exit 0
fi

# Perguntar se deseja iniciar o servidor agora
read -p "Deseja iniciar o servidor agora? (s/n): " iniciar

if [[ $iniciar == "s" || $iniciar == "S" ]]; then
    echo "Iniciando o servidor..."
    cd backend/scraper
    python3 run.py --mongodb
else
    echo "Para iniciar o servidor manualmente execute:"
    echo "cd backend/scraper && python3 run.py --mongodb"
fi

echo "=== Deployment completo! ===" 