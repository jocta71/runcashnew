#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Arquivo de inicialização do sistema RunCash
Configurado para integrar com frontend no Vercel
"""

import sys
import os
import argparse
import subprocess
import time

def main():
    """Função principal de inicialização"""
    parser = argparse.ArgumentParser(description='Sistema RunCash - Inicializador')
    parser.add_argument('--mongodb', action='store_true', help='Usar MongoDB como fonte de dados')
    parser.add_argument('--simulate', action='store_true', help='Iniciar com simulador de dados')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Host para o servidor')
    parser.add_argument('--port', type=int, default=5000, help='Porta para o servidor')
    
    args = parser.parse_args()
    
    # Construir comando para executar app_integrado.py
    cmd = [sys.executable, 'app_integrado.py']
    
    # Adicionar argumentos
    if args.host:
        cmd.extend(['--host', args.host])
    if args.port:
        cmd.extend(['--port', str(args.port)])
    if args.mongodb:
        cmd.append('--mongodb')
    if args.simulate:
        cmd.append('--simulate')
    
    print(f"Executando: {' '.join(cmd)}")
    
    # Exibir informações sobre a API e frontend
    print("\n=== RUNCASH API & FRONTEND ===")
    print(f"🚀 API Backend: http://{args.host}:{args.port}/")
    print("📱 Frontend (Vercel): https://runcashnew-frontend-nu.vercel.app/")
    print("\n📍 Endpoints da API:")
    print("  • /api/status                - Verifica se a API está online")
    print("  • /api/roletas               - Lista de roletas")
    print("  • /api/roletas/:id           - Detalhes de uma roleta")
    print("  • /api/roletas/:id/numeros   - Números de uma roleta")
    print("  • /api/events                - SSE para atualizações em tempo real")
    print("\n💻 Instruções para integração:")
    print("  1. Certifique-se de que esta API esteja acessível publicamente")
    print("  2. No frontend, atualize a URL da API para este endereço")
    print("  3. Teste a conexão em /api/status")
    print("===============================\n")
    
    # Executar o comando
    subprocess.run(cmd)

if __name__ == "__main__":
    main() 