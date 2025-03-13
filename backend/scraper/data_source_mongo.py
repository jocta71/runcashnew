#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Implementação de fonte de dados MongoDB para o sistema
"""

import logging
import hashlib
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
import os
import pymongo

# Importações locais
from scraper_core import DataSourceInterface, determinar_cor_numero
from mongo_config import (
    conectar_mongodb, inicializar_colecoes, 
    roleta_para_documento, numero_para_documento
)
from analytics import calcular_estatisticas_diarias, detectar_sequencias
from config import logger

class MongoDataSource(DataSourceInterface):
    """Implementação de fonte de dados usando MongoDB"""
    
    def __init__(self):
        """Inicializa a fonte de dados MongoDB"""
        # Silenciar pymongo
        logging.getLogger("pymongo").setLevel(logging.CRITICAL)
        
        mongodb_uri = os.environ.get('MONGODB_URI', 'mongodb://localhost:27017/runcash')
        db_name = os.environ.get('MONGODB_DB_NAME', 'runcash')
        
        # Conectar ao MongoDB sem logs
        self.client = pymongo.MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        self.db = self.client[db_name]
        
        # Verificar conexão sem logs
        try:
            self.client.server_info()
            # Sem logging aqui
        except Exception as e:
            # Erro crítico, exibir apenas se for fatal
            raise Exception(f"Falha na conexão com MongoDB: {str(e)}")
        
        try:
            # Conectar ao MongoDB e inicializar coleções
            self.colecoes = inicializar_colecoes()
            logger.info("Fonte de dados MongoDB inicializada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar fonte de dados MongoDB: {str(e)}")
            raise
    
    def garantir_roleta_existe(self, roleta_id: str, roleta_nome: str) -> str:
        """
        Verifica se a roleta existe, e a insere caso não exista
        
        Args:
            roleta_id (str): ID da roleta
            roleta_nome (str): Nome da roleta
            
        Returns:
            str: ID da roleta no MongoDB
        """
        try:
            # Gerar UUID determinístico
            roleta_id_hash = hashlib.md5(str(roleta_id).encode()).hexdigest()
            roleta_uuid = str(uuid.UUID(roleta_id_hash))
            
            # Verificar se a roleta já existe
            if not self.colecoes['roletas'].find_one({"_id": roleta_uuid}):
                # Criar documento e inserir
                documento = roleta_para_documento(roleta_uuid, roleta_nome)
                self.colecoes['roletas'].insert_one(documento)
                logger.info(f"Roleta {roleta_nome} (ID: {roleta_uuid}) criada no MongoDB")
            
            return roleta_uuid
        except Exception as e:
            logger.error(f"Erro ao garantir existência da roleta {roleta_nome}: {str(e)}")
            return roleta_id
    
    def obter_roletas(self) -> List[Dict[str, Any]]:
        """
        Obtém todas as roletas
        
        Returns:
            List[Dict[str, Any]]: Lista de roletas
        """
        try:
            # Obter todas as roletas ativas
            roletas = list(self.colecoes['roletas'].find({"ativa": True}))
            
            # Converter _id para string (já que é ObjectId no MongoDB)
            for roleta in roletas:
                roleta['id'] = roleta.pop('_id')
            
            return roletas
        except Exception as e:
            logger.error(f"Erro ao obter roletas: {str(e)}")
            return []
    
    def obter_ultimos_numeros(self, roleta_id: str, limite: int = 10) -> List[int]:
        """
        Obtém os últimos números para uma roleta específica
        
        Args:
            roleta_id (str): ID da roleta
            limite (int, optional): Limite de números. Defaults to 10.
            
        Returns:
            List[int]: Lista dos últimos números
        """
        try:
            # Gerar UUID determinístico se necessário
            if len(roleta_id) != 36:  # Não é um UUID
                roleta_id_hash = hashlib.md5(str(roleta_id).encode()).hexdigest()
                roleta_id = str(uuid.UUID(roleta_id_hash))
            
            # Consultar os últimos números da roleta
            numeros_docs = list(self.colecoes['roleta_numeros']
                .find({"roleta_id": roleta_id})
                .sort("timestamp", -1)
                .limit(limite))
            
            # Extrair apenas os números
            return [doc['numero'] for doc in numeros_docs]
        except Exception as e:
            logger.error(f"Erro ao obter últimos números para roleta {roleta_id}: {str(e)}")
            return []
    
    def obter_cor_numero(self, numero: int) -> str:
        """
        Obtém a cor de um número
        
        Args:
            numero (int): Número da roleta
            
        Returns:
            str: Cor do número (verde, vermelho ou preto)
        """
        return determinar_cor_numero(numero)
    
    def obter_timestamp_numero(self, roleta_id: str, numero: int, indice: int) -> str:
        """
        Obtém o timestamp de um número específico
        
        Args:
            roleta_id (str): ID da roleta
            numero (int): Número da roleta
            indice (int): Índice do número na lista
            
        Returns:
            str: Timestamp em formato ISO
        """
        try:
            # Gerar UUID determinístico se necessário
            if len(roleta_id) != 36:  # Não é um UUID
                roleta_id_hash = hashlib.md5(str(roleta_id).encode()).hexdigest()
                roleta_id = str(uuid.UUID(roleta_id_hash))
            
            # Tentar obter o timestamp do número
            numero_doc = self.colecoes['roleta_numeros'].find_one(
                {"roleta_id": roleta_id, "numero": numero},
                sort=[("timestamp", -1)],
                skip=indice
            )
            
            if numero_doc and 'timestamp' in numero_doc:
                # Converter para string ISO
                return numero_doc['timestamp'].isoformat()
            
            # Fallback: usar timestamp atual
            return datetime.now().isoformat()
        except Exception as e:
            logger.error(f"Erro ao obter timestamp para número {numero} da roleta {roleta_id}: {str(e)}")
            return datetime.now().isoformat()
    
    def inserir_numero(self, roleta_id: str, roleta_nome: str, numero: int, 
                      cor: str = None, timestamp: str = None) -> bool:
        """
        Insere um novo número para uma roleta
        
        Args:
            roleta_id (str): ID da roleta
            roleta_nome (str): Nome da roleta
            numero (int): Número sorteado
            cor (str, optional): Cor do número. Defaults to None.
            timestamp (str, optional): Timestamp do evento. Defaults to None.
            
        Returns:
            bool: True se inserido com sucesso, False caso contrário
        """
        try:
            # Criar documento
            documento = numero_para_documento(
                roleta_id=roleta_id,
                roleta_nome=roleta_nome,
                numero=numero,
                cor=cor,
                timestamp=timestamp
            )
            
            # Inserir no MongoDB
            result = self.colecoes['roleta_numeros'].insert_one(documento)
            
            if result.inserted_id:
                logger.info(f"Número {numero} inserido para roleta {roleta_nome}")
                
                # Atualizar estatísticas (em thread separada para não bloquear)
                try:
                    import threading
                    threading.Thread(
                        target=self.atualizar_estatisticas_e_sequencias,
                        args=(roleta_id, roleta_nome),
                        daemon=True
                    ).start()
                except Exception as e:
                    logger.error(f"Erro ao iniciar thread de atualização de estatísticas: {str(e)}")
                
                return True
            
            return False
        except Exception as e:
            logger.error(f"Erro ao inserir número {numero} para roleta {roleta_nome}: {str(e)}")
            return False
    
    def atualizar_estatisticas_e_sequencias(self, roleta_id: str, roleta_nome: str) -> None:
        """
        Atualiza estatísticas e sequências para uma roleta
        
        Args:
            roleta_id (str): ID da roleta
            roleta_nome (str): Nome da roleta
        """
        try:
            # Calcular estatísticas diárias para a data atual
            calcular_estatisticas_diarias(roleta_id)
            
            # Detectar sequências
            detectar_sequencias(roleta_id)
            
            logger.debug(f"Estatísticas e sequências atualizadas para roleta {roleta_nome}")
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas e sequências para roleta {roleta_nome}: {str(e)}")
    
    def obter_estatisticas_diarias(self, roleta_id: str, data: datetime = None) -> Dict[str, Any]:
        """
        Obtém estatísticas diárias para uma roleta
        
        Args:
            roleta_id (str): ID da roleta
            data (datetime, optional): Data para obter estatísticas. Defaults to None (hoje).
            
        Returns:
            Dict[str, Any]: Estatísticas diárias
        """
        try:
            # Gerar UUID determinístico se necessário
            if len(roleta_id) != 36:  # Não é um UUID
                roleta_id_hash = hashlib.md5(str(roleta_id).encode()).hexdigest()
                roleta_id = str(uuid.UUID(roleta_id_hash))
            
            # Usar data atual se não especificada
            if data is None:
                data = datetime.now()
            
            # Formatar data como string YYYY-MM-DD
            data_str = data.strftime("%Y-%m-%d")
            
            # Consultar estatísticas no MongoDB
            estatisticas = self.colecoes['roleta_estatisticas_diarias'].find_one({
                "roleta_id": roleta_id,
                "data": data_str
            })
            
            if not estatisticas:
                # Se não existirem estatísticas, calculá-las
                return calcular_estatisticas_diarias(roleta_id, data)
            
            # Remover _id do documento
            if '_id' in estatisticas:
                del estatisticas['_id']
            
            return estatisticas
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas diárias para roleta {roleta_id}: {str(e)}")
            return None
    
    def obter_sequencias(self, roleta_id: str, tipo: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtém sequências para uma roleta
        
        Args:
            roleta_id (str): ID da roleta
            tipo (Optional[str], optional): Tipo de sequência. Defaults to None (todos).
            
        Returns:
            List[Dict[str, Any]]: Lista de sequências
        """
        try:
            # Gerar UUID determinístico se necessário
            if len(roleta_id) != 36:  # Não é um UUID
                roleta_id_hash = hashlib.md5(str(roleta_id).encode()).hexdigest()
                roleta_id = str(uuid.UUID(roleta_id_hash))
            
            # Preparar filtro
            filtro = {"roleta_id": roleta_id}
            if tipo:
                filtro["tipo"] = tipo
            
            # Consultar sequências no MongoDB
            sequencias = list(self.colecoes['roleta_sequencias']
                .find(filtro)
                .sort([("comprimento", -1), ("inicio_timestamp", -1)])
                .limit(50))
            
            # Converter _id para string e timestamps para ISO
            for seq in sequencias:
                if '_id' in seq:
                    seq['id'] = str(seq.pop('_id'))
                if 'inicio_timestamp' in seq:
                    seq['inicio_timestamp'] = seq['inicio_timestamp'].isoformat()
                if 'fim_timestamp' in seq:
                    seq['fim_timestamp'] = seq['fim_timestamp'].isoformat()
                if 'criado_em' in seq:
                    seq['criado_em'] = seq['criado_em'].isoformat()
                if 'atualizado_em' in seq:
                    seq['atualizado_em'] = seq['atualizado_em'].isoformat()
            
            return sequencias
        except Exception as e:
            logger.error(f"Erro ao obter sequências para roleta {roleta_id}: {str(e)}")
            return [] 