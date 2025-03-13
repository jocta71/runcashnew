#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para migrar dados do Supabase para MongoDB
"""

import os
import logging
import json
import requests
from dotenv import load_dotenv
from datetime import datetime
import re
import sys

# Importar configuração MongoDB
from mongo_config import (
    conectar_mongodb, inicializar_colecoes, 
    roleta_para_documento, numero_para_documento
)

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('migrar_para_mongo')

# Configuração do Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://evzqzghxuttctbxgohpx.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ')

def obter_dados_supabase(tabela, limite=1000):
    """
    Obtém dados de uma tabela do Supabase
    
    Args:
        tabela (str): Nome da tabela
        limite (int, optional): Limite de registros. Defaults to 1000.
        
    Returns:
        list: Lista de dados obtidos do Supabase
    """
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json"
    }
    
    url = f"{SUPABASE_URL}/rest/v1/{tabela}?limit={limite}"
    
    try:
        logger.info(f"Obtendo dados da tabela {tabela} do Supabase...")
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            dados = response.json()
            logger.info(f"Obtidos {len(dados)} registros da tabela {tabela}")
            return dados
        else:
            logger.error(f"Erro ao obter dados de {tabela}: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"Erro ao obter dados de {tabela}: {str(e)}")
        return []

def migrar_roletas(colecao_mongo):
    """
    Migra roletas do Supabase para MongoDB
    
    Args:
        colecao_mongo: Coleção MongoDB para roletas
        
    Returns:
        int: Número de roletas migradas
    """
    try:
        roletas_supabase = obter_dados_supabase("roletas")
        
        if not roletas_supabase:
            logger.warning("Nenhuma roleta encontrada no Supabase para migração")
            return 0
        
        # Converter registros do Supabase para formato MongoDB
        roletas_migradas = 0
        for roleta in roletas_supabase:
            roleta_id = roleta.get("id")
            roleta_nome = roleta.get("nome")
            roleta_tipo = roleta.get("tipo", "ao_vivo")
            
            if not roleta_id or not roleta_nome:
                logger.warning(f"Roleta sem ID ou nome: {roleta}")
                continue
                
            # Verificar se já existe no MongoDB
            if colecao_mongo.find_one({"_id": roleta_id}):
                logger.debug(f"Roleta {roleta_nome} (ID: {roleta_id}) já existe no MongoDB")
                continue
                
            # Criar documento e inserir
            documento = roleta_para_documento(roleta_id, roleta_nome, roleta_tipo)
            colecao_mongo.insert_one(documento)
            roletas_migradas += 1
            
        logger.info(f"Migradas {roletas_migradas} roletas para MongoDB")
        return roletas_migradas
    except Exception as e:
        logger.error(f"Erro ao migrar roletas: {str(e)}")
        return 0

def migrar_numeros(colecao_mongo, colecao_roletas):
    """
    Migra números da roleta do Supabase para MongoDB
    
    Args:
        colecao_mongo: Coleção MongoDB para números da roleta
        colecao_roletas: Coleção MongoDB para roletas
        
    Returns:
        int: Número de registros migrados
    """
    try:
        numeros_supabase = obter_dados_supabase("roleta_numeros")
        
        if not numeros_supabase:
            logger.warning("Nenhum número encontrado no Supabase para migração")
            return 0
        
        # Converter registros do Supabase para formato MongoDB
        numeros_migrados = 0
        for numero in numeros_supabase:
            try:
                roleta_id = numero.get("roleta_id")
                roleta_nome = numero.get("roleta_nome")
                numero_valor = numero.get("numero")
                cor = numero.get("cor")
                timestamp = numero.get("timestamp") or numero.get("created_at")
                
                if not roleta_id or not roleta_nome or numero_valor is None:
                    logger.warning(f"Registro inválido: {numero}")
                    continue
                    
                # Garantir que roleta existe no MongoDB
                if not colecao_roletas.find_one({"_id": roleta_id}):
                    logger.warning(f"Roleta {roleta_nome} (ID: {roleta_id}) não existe no MongoDB")
                    documento_roleta = roleta_para_documento(roleta_id, roleta_nome)
                    colecao_roletas.insert_one(documento_roleta)
                    logger.info(f"Roleta {roleta_nome} (ID: {roleta_id}) criada no MongoDB")
                
                # Converter número para inteiro se for string
                if isinstance(numero_valor, str):
                    numero_valor = int(re.sub(r'[^\d]', '', numero_valor))
                
                # Criar documento e inserir
                documento = numero_para_documento(
                    roleta_id=roleta_id,
                    roleta_nome=roleta_nome,
                    numero=numero_valor,
                    cor=cor,
                    timestamp=timestamp
                )
                
                # Verificar se já existe registro similar
                filtro = {
                    "roleta_id": roleta_id,
                    "numero": numero_valor,
                    "timestamp": documento["timestamp"]
                }
                
                if not colecao_mongo.find_one(filtro):
                    colecao_mongo.insert_one(documento)
                    numeros_migrados += 1
                
            except Exception as e:
                logger.error(f"Erro ao migrar registro: {str(e)}, registro: {numero}")
                continue
                
        logger.info(f"Migrados {numeros_migrados} números para MongoDB")
        return numeros_migrados
    except Exception as e:
        logger.error(f"Erro ao migrar números: {str(e)}")
        return 0

def migrar_dados():
    """
    Migra todos os dados do Supabase para MongoDB
    
    Returns:
        tuple: (roletas_migradas, numeros_migrados)
    """
    try:
        # Conectar ao MongoDB e inicializar coleções
        _, _ = conectar_mongodb()
        colecoes = inicializar_colecoes()
        
        # Migrar roletas
        roletas_migradas = migrar_roletas(colecoes['roletas'])
        
        # Migrar números
        numeros_migrados = migrar_numeros(colecoes['roleta_numeros'], colecoes['roletas'])
        
        return roletas_migradas, numeros_migrados
    except Exception as e:
        logger.error(f"Erro durante a migração: {str(e)}")
        return 0, 0

if __name__ == "__main__":
    logger.info("Iniciando migração de dados do Supabase para MongoDB...")
    
    roletas, numeros = migrar_dados()
    
    logger.info(f"Migração concluída! Roletas: {roletas}, Números: {numeros}")
    
    if roletas == 0 and numeros == 0:
        logger.warning("Nenhum dado foi migrado. Verifique as conexões e os dados de origem.")
        sys.exit(1)
    
    logger.info("Migração concluída com sucesso!")
    sys.exit(0) 