#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Módulo principal do sistema de scraper de roletas.
Este arquivo coordena a inicialização dos componentes do sistema.
"""

import os
import sys
import logging
import time
import traceback
import signal
import threading
from datetime import datetime
import argparse

# Configuração de logging
from config import (
    configurar_logging, 
    AMBIENTE_PROD, 
    MONGODB_ENABLED,
    SUPABASE_ENABLED,
    DEFAULT_HOST,
    DEFAULT_PORT,
    logger
)

# Inicializar logging
configurar_logging()

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Sistema de Scraper de Roletas')
    parser.add_argument('--host', type=str, default=DEFAULT_HOST,
                        help=f'Host para o servidor (padrão: {DEFAULT_HOST})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                        help=f'Porta para o servidor (padrão: {DEFAULT_PORT})')
    parser.add_argument('--mongodb', action='store_true', default=MONGODB_ENABLED,
                        help='Usar MongoDB como fonte de dados')
    parser.add_argument('--supabase', action='store_true', default=SUPABASE_ENABLED,
                        help='Usar Supabase como fonte de dados')
    parser.add_argument('--simulate', action='store_true',
                        help='Iniciar com simulador de dados')
    parser.add_argument('--only-server', action='store_true',
                        help='Iniciar apenas o servidor, sem o scraper')
    return parser.parse_args()

def main():
    """Função principal do sistema"""
    args = parse_args()
    
    logger.info("=" * 50)
    logger.info(f"Iniciando sistema em ambiente {'PRODUÇÃO' if AMBIENTE_PROD else 'DESENVOLVIMENTO'}")
    logger.info(f"Data e hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    # Inicializar fonte de dados
    data_source = None
    if args.mongodb:
        try:
            from data_source_mongo import MongoDataSource
            logger.info("Inicializando fonte de dados MongoDB...")
            data_source = MongoDataSource()
            logger.info("Fonte de dados MongoDB inicializada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar MongoDB: {str(e)}")
            traceback.print_exc()
            if not args.supabase:  # Se MongoDB falhar e Supabase não foi especificado
                sys.exit(1)
    
    if args.supabase or (data_source is None and args.mongodb):
        try:
            from data_source_supabase import SupabaseDataSource
            logger.info("Inicializando fonte de dados Supabase...")
            data_source = SupabaseDataSource()
            logger.info("Fonte de dados Supabase inicializada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar Supabase: {str(e)}")
            traceback.print_exc()
            if data_source is None:  # Se ambas as fontes de dados falharem
                sys.exit(1)
    
    # Capturar sinal de interrupção
    stop_event = threading.Event()
    
    def signal_handler(sig, frame):
        logger.info("Recebido sinal de interrupção, encerrando...")
        stop_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Iniciar scraper em thread separada se não for apenas servidor
    scraper_thread = None
    if not args.only_server:
        # Importar e iniciar scraper
        from scraper_core import scrape_roletas, simulate_roulette_data
        
        scraper_func = simulate_roulette_data if args.simulate else scrape_roletas
        
        logger.info(f"Iniciando {'simulador' if args.simulate else 'scraper'} em thread separada...")
        scraper_thread = threading.Thread(
            target=scraper_func,
            args=(data_source, stop_event),
            daemon=True
        )
        scraper_thread.start()
    
    # Iniciar servidor Flask
    from server import start_server
    
    try:
        logger.info(f"Iniciando servidor na porta {args.port}...")
        start_server(args.host, args.port, data_source)
    except KeyboardInterrupt:
        logger.info("Interrupção do teclado detectada, encerrando aplicação...")
    except Exception as e:
        logger.error(f"Erro ao iniciar servidor: {str(e)}")
        traceback.print_exc()
    finally:
        # Sinalizar para threads pararem
        stop_event.set()
        
        # Aguardar thread do scraper, se existir
        if scraper_thread and scraper_thread.is_alive():
            logger.info("Aguardando encerramento do scraper...")
            scraper_thread.join(timeout=5)
        
        logger.info("Aplicação encerrada")

if __name__ == "__main__":
    main() 