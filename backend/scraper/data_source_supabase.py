#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Implementação de fonte de dados Supabase para o sistema
"""

import logging
import hashlib
import uuid
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
import traceback

from supabase import create_client
from config import SUPABASE_URL, SUPABASE_KEY, logger
from scraper_core import DataSourceInterface, determinar_cor_numero

class SupabaseDataSource(DataSourceInterface):
    """Implementação de fonte de dados usando Supabase"""
    
    def __init__(self):
        """Inicializa a fonte de dados Supabase"""
        try:
            # Garantir que a URL do Supabase esteja corretamente formatada
            supabase_url = SUPABASE_URL
            if supabase_url.startswith('@'):
                supabase_url = supabase_url[1:]
            if not supabase_url.startswith('http'):
                supabase_url = f"https://{supabase_url}"
            
            # Conectar ao Supabase
            self.supabase = create_client(supabase_url, SUPABASE_KEY)
            logger.info("Fonte de dados Supabase inicializada com sucesso")
            
            # Verificar conexão executando uma consulta simples
            self._verificar_tabela()
        except Exception as e:
            logger.error(f"Erro ao inicializar fonte de dados Supabase: {str(e)}")
            logger.error(traceback.format_exc())
            raise
    
    def _verificar_tabela(self):
        """Verifica se a tabela necessária existe no Supabase"""
        try:
            # Verificar se a tabela roleta_numeros existe
            response = self.supabase.table('roleta_numeros').select('*').limit(1).execute()
            logger.info("Tabela roleta_numeros verificada com sucesso no Supabase")
            return True
        except Exception as e:
            logger.error(f"Erro ao verificar tabela roleta_numeros: {str(e)}")
            logger.error("Isso pode indicar que a tabela não existe ou há problemas de acesso")
            return False
    
    def garantir_roleta_existe(self, roleta_id: str, roleta_nome: str) -> str:
        """
        Verifica se a roleta existe, e a insere caso não exista
        
        Args:
            roleta_id (str): ID da roleta
            roleta_nome (str): Nome da roleta
            
        Returns:
            str: ID da roleta no Supabase
        """
        try:
            # Gerar UUID determinístico
            roleta_id_hash = hashlib.md5(str(roleta_id).encode()).hexdigest()
            roleta_uuid = str(uuid.UUID(roleta_id_hash))
            
            # Verificar se a roleta já existe
            response = self.supabase.table('roletas').select('*').eq('id', roleta_uuid).execute()
            
            if not response.data:
                # Criar e inserir a roleta
                atual = datetime.now().isoformat()
                roleta_data = {
                    'id': roleta_uuid,
                    'nome': roleta_nome,
                    'identificador_original': roleta_id,
                    'ativa': True,
                    'created_at': atual,
                    'updated_at': atual
                }
                
                self.supabase.table('roletas').insert(roleta_data).execute()
                logger.info(f"Roleta {roleta_nome} (ID: {roleta_uuid}) criada no Supabase")
            
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
            response = self.supabase.table('roletas').select('*').eq('ativa', True).execute()
            return response.data
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
            response = self.supabase.table('roleta_numeros') \
                .select('numero') \
                .eq('roleta_id', roleta_id) \
                .order('created_at', desc=True) \
                .limit(limite) \
                .execute()
            
            # Extrair apenas os números
            if response.data:
                return [item['numero'] for item in response.data]
            
            return []
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
            
            # Consultar o timestamp do número
            response = self.supabase.table('roleta_numeros') \
                .select('created_at') \
                .eq('roleta_id', roleta_id) \
                .eq('numero', numero) \
                .order('created_at', desc=True) \
                .limit(indice + 1) \
                .execute()
            
            if response.data and len(response.data) > indice:
                return response.data[indice]['created_at']
            
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
            # Se a cor não foi informada, determinar
            if not cor:
                cor = self.obter_cor_numero(numero)
            
            # Se o timestamp não foi informado, usar o atual
            if not timestamp:
                timestamp = datetime.now().isoformat()
            
            # Preparar dados para inserção
            dados = {
                'roleta_id': roleta_id,
                'roleta_nome': roleta_nome,
                'numero': numero,
                'cor': cor,
                'created_at': timestamp
            }
            
            # Inserir no Supabase
            response = self.supabase.table('roleta_numeros').insert(dados).execute()
            
            if response.data:
                logger.info(f"Número {numero} inserido para roleta {roleta_nome}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Erro ao inserir número {numero} para roleta {roleta_nome}: {str(e)}")
            
            # Tentar sem o campo created_at (para retrocompatibilidade)
            try:
                dados = {
                    'roleta_id': roleta_id,
                    'roleta_nome': roleta_nome,
                    'numero': numero,
                    'cor': cor
                }
                
                # Inserir no Supabase sem o campo created_at
                response = self.supabase.table('roleta_numeros').insert(dados).execute()
                
                if response.data:
                    logger.info(f"Número {numero} inserido para roleta {roleta_nome} (sem created_at)")
                    return True
            except Exception as e2:
                logger.error(f"Erro na segunda tentativa de inserção: {str(e2)}")
            
            return False
    
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
            
            # Executar RPC para obter estatísticas
            # Esta é uma função armazenada no Supabase que calcula as estatísticas diárias
            response = self.supabase.rpc(
                'obter_estatisticas_diarias', 
                {"p_roleta_id": roleta_id, "p_data": data_str}
            ).execute()
            
            if response.data:
                return response.data[0] if isinstance(response.data, list) else response.data
            
            # Se não houver dados, retornar estrutura vazia
            return {
                "roleta_id": roleta_id,
                "data": data_str,
                "total_numeros": 0,
                "distribuicao_numeros": [],
                "distribuicao_cores": {"vermelho": 0, "preto": 0, "verde": 0},
                "numeros_mais_frequentes": [],
                "numeros_menos_frequentes": []
            }
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
            
            # Preparar consulta
            query = self.supabase.table('roleta_sequencias') \
                .select('*') \
                .eq('roleta_id', roleta_id)
            
            # Adicionar filtro por tipo, se especificado
            if tipo:
                query = query.eq('tipo', tipo)
            
            # Executar consulta ordenando por comprimento e timestamp de início
            response = query \
                .order('comprimento', desc=True) \
                .order('inicio_timestamp', desc=True) \
                .limit(50) \
                .execute()
            
            if response.data:
                return response.data
            
            return []
        except Exception as e:
            logger.error(f"Erro ao obter sequências para roleta {roleta_id}: {str(e)}")
            return [] 