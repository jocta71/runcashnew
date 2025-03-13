#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para inserir números de teste nas roletas
"""

import sys
from datetime import datetime
from data_source_mongo import MongoDataSource
from event_manager import event_manager

def insert_test_number(roleta_nome, numero):
    """Insere um número de teste em uma roleta específica"""
    print(f"Inserindo número {numero} para roleta '{roleta_nome}'...")
    
    # Inicializar fonte de dados
    data_source = MongoDataSource()
    
    # Buscar roleta pelo nome
    roletas = list(data_source.db.roletas.find({"nome": roleta_nome}, {'_id': 0}))
    
    if not roletas:
        print(f"Erro: Roleta '{roleta_nome}' não encontrada!")
        return False
    
    roleta = roletas[0]
    roleta_id = roleta.get('id')
    
    # Se não tiver ID, gerar um baseado no nome
    if not roleta_id:
        import hashlib
        import uuid
        roleta_id_hash = hashlib.md5(roleta_nome.encode()).hexdigest()
        roleta_id = str(uuid.UUID(roleta_id_hash))
        
        # Atualizar roleta com o ID
        data_source.db.roletas.update_one(
            {"nome": roleta_nome},
            {"$set": {"id": roleta_id}}
        )
        print(f"ID gerado para roleta: {roleta_id}")
    
    # Determinar cor do número
    cor = 'verde' if numero == 0 else ('vermelho' if numero % 2 == 1 else 'preto')
    
    # Inserir número
    timestamp = datetime.now().isoformat()
    sucesso = data_source.inserir_numero(roleta_id, roleta_nome, numero, cor, timestamp)
    
    if sucesso:
        print(f"Número {numero} inserido com sucesso!")
        
        # Notificar clientes SSE
        event_manager.notify_clients({
            "type": "new_number",
            "roleta_id": roleta_id,
            "roleta_nome": roleta_nome,
            "numero": numero,
            "cor": cor,
            "timestamp": timestamp
        })
        
        return True
    else:
        print(f"Erro ao inserir número {numero}!")
        return False

if __name__ == "__main__":
    # Verificar argumentos
    if len(sys.argv) < 3:
        print("Uso: python add_test_number.py <nome_roleta> <numero>")
        sys.exit(1)
    
    roleta_nome = sys.argv[1]
    numero = int(sys.argv[2])
    
    # Validar número
    if numero < 0 or numero > 36:
        print("Erro: O número deve estar entre 0 e 36!")
        sys.exit(1)
    
    # Inserir número
    if insert_test_number(roleta_nome, numero):
        print("Operação concluída com sucesso!")
    else:
        print("Falha na operação!")
        sys.exit(1) 