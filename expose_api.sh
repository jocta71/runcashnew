#!/bin/bash

# Script para expor a API RunCash usando ngrok para testes

echo "=== RunCash API - Exposição para testes ==="
echo "Este script ajuda a expor a API para testes com o frontend no Vercel"

# Verificar se ngrok está instalado
if ! command -v ngrok &> /dev/null; then
    echo "ngrok não encontrado!"
    echo "Por favor, instale o ngrok: https://ngrok.com/download"
    exit 1
fi

# Perguntar porta (default: 5000)
read -p "Em qual porta a API está rodando? [5000]: " porta
porta=${porta:-5000}

echo "Expondo a API na porta $porta para a internet..."
echo "IMPORTANTE: Após o ngrok iniciar, copie a URL https gerada (algo como https://xxxx.ngrok.io)"
echo "e atualize a variável API_URL no seu frontend."
echo ""
echo "Pressione Ctrl+C para encerrar a exposição quando terminar os testes."
echo ""

# Iniciar ngrok
ngrok http $porta 