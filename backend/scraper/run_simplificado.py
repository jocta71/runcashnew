#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Executor do scraper simplificado para MongoDB
(Versão otimizada para evitar duplicação de números)
"""

import sys
import os
import argparse
import time
import threading
import logging
import signal
import subprocess

# Configuração de argumentos
parser = argparse.ArgumentParser(description='RunCash Scraper melhorado para MongoDB')
parser.add_argument('--mongodb', action='store_true', help='Usar MongoDB em vez de Supabase')
parser.add_argument('--timeout', type=int, default=0, help='Tempo máximo de execução em segundos (0 = sem limite)')
parser.add_argument('--verbose', action='store_true', help='Mostrar informações detalhadas')
args = parser.parse_args()

# Configurar logging básico
log_level = logging.INFO if args.verbose else logging.WARNING
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger('run_scraper')

# Iniciar API integrada se usando MongoDB
if args.mongodb:
    from data_source_mongo import MongoDataSource
    from scraper_simplificado import scrape_roletas
    
    try:
        # Iniciar MongoDB
        db = MongoDataSource()
        logger.info("Inicializando MongoDB")
        
        # Iniciar API em thread separada
        api_process = None
        
        def iniciar_api():
            global api_process
            
            cmd = [sys.executable, "app_integrado.py", "--host", "0.0.0.0", "--port", "5000", "--mongodb"]
            api_process = subprocess.Popen(cmd, shell=False)
            logger.info(f"API iniciada com PID {api_process.pid}")
            return api_process
        
        # Iniciar a API
        iniciar_api()
        
        # Definir handler para SIGINT (Ctrl+C)
        def signal_handler(sig, frame):
            logger.info("Sinal de interrupção recebido. Encerrando...")
            if api_process:
                logger.info(f"Terminando processo API (PID: {api_process.pid})")
                api_process.terminate()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        
        # Executar o scraper em loop principal
        def executar_scraper():
            try:
                logger.info("Iniciando scraper MongoDB...")
                scrape_roletas(db)
            except Exception as e:
                logger.error(f"Erro ao executar scraper: {str(e)}")
                if api_process:
                    api_process.terminate()
                return False
            return True
        
        # Executar com timeout se especificado
        if args.timeout > 0:
            logger.info(f"Executando com timeout de {args.timeout} segundos")
            inicio = time.time()
            while time.time() - inicio < args.timeout:
                if not executar_scraper():
                    break
                time.sleep(1)
            logger.info("Timeout atingido, encerrando...")
            if api_process:
                api_process.terminate()
        else:
            # Executar sem timeout
            executar_scraper()
    
    except KeyboardInterrupt:
        logger.info("Interrompido pelo usuário")
        if api_process:
            api_process.terminate()
    except Exception as e:
        logger.error(f"Erro fatal: {str(e)}")
        if api_process:
            api_process.terminate()
        sys.exit(1)

else:
    print("ERRO: Este script só funciona com MongoDB. Use --mongodb para habilitar.")
    sys.exit(1) 