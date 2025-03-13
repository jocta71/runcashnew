#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para criar uma solução alternativa e temporária para o problema da coluna created_at
Este script implementará uma versão modificada da função de inserção que não depende da coluna created_at
"""

import os
import logging
import json
import requests
import re
import uuid
import hashlib
from datetime import datetime
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('workaround')

# Configuração do Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://evzqzghxuttctbxgohpx.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ')

def garantir_roleta_existe(roleta_id, roleta_nome):
    """
    Verifica se a roleta existe na tabela roletas, 
    e a insere caso não exista
    """
    try:
        # Gerar o mesmo UUID determinístico baseado no ID da roleta
        roleta_id_hash = hashlib.md5(str(roleta_id).encode()).hexdigest()
        roleta_uuid = str(uuid.UUID(roleta_id_hash))
        
        # Determinar o tipo de roleta com base no nome
        tipo_roleta = "ao_vivo"  # Valor padrão
        if "auto" in roleta_nome.lower() or "speed" in roleta_nome.lower():
            tipo_roleta = "automatica"
        elif "lightning" in roleta_nome.lower():
            tipo_roleta = "especial"
        
        # Preparar dados para inserção
        dados_roleta = {
            "id": roleta_uuid,
            "nome": roleta_nome,
            "tipo": tipo_roleta,
            "provedor": "Evolution Gaming",  # Valor padrão
            "ativa": True
        }
        
        # Verificar se a roleta já existe
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Verificar se a roleta já existe
        check_url = f"{SUPABASE_URL}/rest/v1/roletas?id=eq.{roleta_uuid}&select=id"
        check_response = requests.get(check_url, headers=headers)
        
        if check_response.status_code == 200 and check_response.json():
            logger.info(f"Roleta {roleta_nome} (ID: {roleta_uuid}) já existe")
            return roleta_uuid
        
        # Inserir nova roleta
        insert_url = f"{SUPABASE_URL}/rest/v1/roletas"
        insert_response = requests.post(insert_url, json=dados_roleta, headers=headers)
        
        if insert_response.status_code >= 200 and insert_response.status_code < 300:
            logger.info(f"Roleta {roleta_nome} (ID: {roleta_uuid}) inserida com sucesso")
            return roleta_uuid
        else:
            logger.error(f"Erro ao inserir roleta {roleta_nome}: {insert_response.text}")
            return None
    except Exception as e:
        logger.error(f"Erro ao verificar/inserir roleta {roleta_nome}: {str(e)}")
        return None

def inserir_numero_rollback(roleta_id, roleta_nome, numero, timestamp=None):
    """
    Versão alternativa da função inserir_numero_direto_api que não depende da coluna created_at
    """
    try:
        # Usar timestamp atual se não for fornecido
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        
        # Validar o número
        if isinstance(numero, str):
            numero_int = int(re.sub(r'[^\d]', '', numero))
        else:
            numero_int = int(numero)
        
        if not (0 <= numero_int <= 36):
            logger.warning(f"Número inválido para inserção: {numero}")
            return False
        
        # Garantir que a roleta existe na tabela roletas
        roleta_uuid = garantir_roleta_existe(roleta_id, roleta_nome)
        if not roleta_uuid:
            logger.error(f"Não foi possível garantir a existência da roleta {roleta_nome} (ID: {roleta_id})")
            return False
        
        # Determinar a cor do número
        cor = 'verde' if numero_int == 0 else 'vermelho' if numero_int % 2 == 1 else 'preto'
        
        # Exceções específicas para a roleta europeia
        numeros_vermelhos = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
        if numero_int > 0:  # 0 é verde
            cor = 'vermelho' if numero_int in numeros_vermelhos else 'preto'
        
        # Criar a URL e a query diretamente usando RPC
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json"
        }
        
        # Usar comando SQL direto para inserir sem depender da coluna created_at
        sql_data = {
            "command": f"""
            INSERT INTO roleta_numeros (roleta_id, roleta_nome, numero, cor, timestamp)
            VALUES ('{roleta_uuid}', '{roleta_nome}', {numero_int}, '{cor}', '{timestamp}')
            """
        }
        
        # Tentar usar a função SQL para inserção direta
        url = f"{SUPABASE_URL}/rest/v1/rpc/sql"
        response = requests.post(url, json=sql_data, headers=headers)
        
        if response.status_code >= 200 and response.status_code < 300:
            logger.info(f"NOVO NÚMERO: {numero_int} para {roleta_nome} (ID: {roleta_uuid}) - MÉTODO ALTERNATIVO")
            print(f"{datetime.now().strftime('%H:%M:%S')} - NOVO NÚMERO: {numero_int} para {roleta_nome}")
            return True
        else:
            logger.error(f"Erro ao tentar método alternativo: {response.status_code} - {response.text}")
            
            # Tentar outra solução: inserção manual
            logger.info("Tentando inserção usando campos mínimos (método de fallback)...")
            
            # Preparar dados para inserção com campos mínimos
            fallback_data = {
                "roleta_id": roleta_uuid,
                "roleta_nome": roleta_nome,
                "numero": numero_int,
                "timestamp": timestamp
            }
            
            fallback_url = f"{SUPABASE_URL}/rest/v1/roleta_numeros"
            fallback_response = requests.post(fallback_url, json=fallback_data, headers=headers)
            
            if fallback_response.status_code >= 200 and fallback_response.status_code < 300:
                logger.info(f"NOVO NÚMERO: {numero_int} para {roleta_nome} (ID: {roleta_uuid}) - MÉTODO FALLBACK")
                print(f"{datetime.now().strftime('%H:%M:%S')} - NOVO NÚMERO: {numero_int} para {roleta_nome}")
                return True
            else:
                logger.error(f"Erro no método fallback: {fallback_response.status_code} - {fallback_response.text}")
                return False
    
    except Exception as e:
        logger.error(f"Erro ao inserir número {numero} para a roleta {roleta_nome}: {str(e)}")
        return False

def demonstracao():
    """Função para demonstrar o workaround"""
    logger.info("Executando demonstração do método alternativo...")
    
    # Roletas para teste
    roletas_teste = [
        {"id": "2010016", "nome": "Immersive Roulette"},
        {"id": "2380335", "nome": "Brazilian Mega Roulette"},
        {"id": "2010065", "nome": "Bucharest Auto-Roulette"}
    ]
    
    # Tentar inserir um número para cada roleta de teste
    for roleta in roletas_teste:
        numero = 7  # Número de teste
        logger.info(f"Testando inserção para {roleta['nome']} (ID: {roleta['id']})...")
        resultado = inserir_numero_rollback(roleta['id'], roleta['nome'], numero)
        if resultado:
            logger.info(f"SUCESSO! Número {numero} inserido para {roleta['nome']}")
        else:
            logger.error(f"FALHA! Não foi possível inserir o número {numero} para {roleta['nome']}")
    
    logger.info("Demonstração concluída!")

if __name__ == "__main__":
    logger.info("Iniciando script de solução alternativa...")
    demonstracao() 