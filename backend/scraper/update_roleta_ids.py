#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para atualizar todas as roletas no MongoDB, garantindo que todas tenham IDs corretos
"""

import hashlib
import uuid
from datetime import datetime
from bson import ObjectId
from data_source_mongo import MongoDataSource

def update_roleta_ids():
    """Atualiza todas as roletas no MongoDB, adicionando IDs se não existirem"""
    print("Atualizando IDs das roletas no MongoDB...")
    
    # Inicializar fonte de dados
    data_source = MongoDataSource()
    
    # Buscar todas as roletas
    roletas = list(data_source.db.roletas.find({}))
    print(f"Encontradas {len(roletas)} roletas no MongoDB")
    
    # Para contabilizar roletas com nomes duplicados
    nome_contador = {}
    
    # Atualizar cada roleta
    for roleta in roletas:
        nome = roleta.get('nome')
        mongo_id = roleta.get('_id')  # Obtém o _id do MongoDB
        
        if not nome:
            print(f"Erro: Roleta sem nome encontrada: {roleta}")
            continue
        
        # Contabilizar ocorrências do nome
        if nome not in nome_contador:
            nome_contador[nome] = 0
        nome_contador[nome] += 1
        
        # Se for uma roleta duplicada, adicionar sufixo ao nome
        nome_efetivo = nome
        if nome_contador[nome] > 1:
            nome_efetivo = f"{nome}_{nome_contador[nome]}"
            # Atualizar o nome da roleta no banco de dados
            data_source.db.roletas.update_one(
                {"_id": mongo_id},
                {"$set": {"nome": nome_efetivo}}
            )
            print(f"Roleta duplicada renomeada: '{nome}' -> '{nome_efetivo}'")
        
        # Verificar se a roleta já tem ID
        roleta_id = roleta.get('id')
        if not roleta_id:
            # Gerar ID baseado no nome
            roleta_id_hash = hashlib.md5(nome_efetivo.encode()).hexdigest()
            roleta_id = str(uuid.UUID(roleta_id_hash))
            
            # Atualizar roleta com o ID
            data_source.db.roletas.update_one(
                {"_id": mongo_id},
                {"$set": {
                    "id": roleta_id,
                    "atualizado_em": datetime.now().isoformat()
                }}
            )
            print(f"Roleta '{nome_efetivo}' atualizada com ID: {roleta_id}")
        else:
            print(f"Roleta '{nome_efetivo}' já possui ID: {roleta_id}")
    
    # Verificar atualizações
    roletas_atualizadas = list(data_source.db.roletas.find({}, {'_id': 0}))
    roletas_sem_id = list(data_source.db.roletas.find({"id": {"$exists": False}}, {'_id': 0}))
    
    print(f"\nTotal de roletas após atualização: {len(roletas_atualizadas)}")
    print(f"Roletas sem ID após atualização: {len(roletas_sem_id)}")
    
    if roletas_sem_id:
        print("ATENÇÃO: Ainda existem roletas sem ID:")
        for roleta in roletas_sem_id:
            print(f"  - {roleta.get('nome', 'SEM NOME')}")
    else:
        print("SUCESSO: Todas as roletas possuem IDs válidos!")
    
    # Listar todas as roletas com seus IDs
    print("\nLista de todas as roletas:")
    for roleta in roletas_atualizadas:
        print(f"  - {roleta.get('nome')}: {roleta.get('id')}")

if __name__ == "__main__":
    update_roleta_ids()
    print("Operação concluída!") 