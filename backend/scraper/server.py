#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API REST para RunCash - Integração com frontend
Suporte a Server-Sent Events (SSE) para atualizações em tempo real
"""

import os
import json
import time
import threading
import logging
import queue
from datetime import datetime
from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import hashlib
import uuid

# Importações locais
from data_source_mongo import MongoDataSource
from event_manager import event_manager, EventManager
from config import DEFAULT_HOST, DEFAULT_PORT, API_VERSION

# Configurar logger
logger = logging.getLogger('runcash_api')
logger.setLevel(logging.INFO)

# Criar a aplicação Flask
app = Flask(__name__)

# Configurar CORS para permitir solicitações do frontend
allowed_origins = os.environ.get('ALLOWED_ORIGINS', 'https://runcashnew-frontend-nu.vercel.app,https://runcashnew.vercel.app,https://seu-projeto.vercel.app,http://localhost:3000,http://localhost:5173')
CORS(app, resources={r"/api/*": {"origins": allowed_origins.split(','), "supports_credentials": True}})

# Fonte de dados
data_source = MongoDataSource()

@app.route('/api/status')
def api_status():
    """Endpoint para verificar se a API está online"""
    return jsonify({
        "status": "online",
        "version": API_VERSION,
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/roletas', methods=['GET'])
def get_roletas():
    """Retorna a lista de roletas disponíveis no MongoDB"""
    roletas = data_source.db.roletas.find({}, {'_id': 0})
    return jsonify(list(roletas))

@app.route('/api/roletas/<roleta_id>', methods=['GET'])
def get_roleta(roleta_id):
    """Retorna informações sobre uma roleta específica pelo ID"""
    roleta = data_source.db.roletas.find_one({'id': roleta_id}, {'_id': 0})
    if not roleta:
        return jsonify({'error': 'Roleta não encontrada'}), 404
    return jsonify(roleta)

@app.route('/api/roletas/<roleta_id>/numeros', methods=['GET'])
def get_roleta_numeros(roleta_id):
    """Retorna os números de uma roleta específica"""
    # Log da requisição
    print(f"[API] Recebida requisição para números da roleta: {roleta_id}")
    
    # Quantidade de números a retornar
    limite = int(request.args.get('limit', 50))
    
    # Gerar UUID determinístico se necessário
    if len(roleta_id) != 36:  # Não é um UUID
        print(f"[API] Convertendo ID não-UUID: {roleta_id}")
        roleta_id_hash = hashlib.md5(str(roleta_id).encode()).hexdigest()
        roleta_id = str(uuid.UUID(roleta_id_hash))
        print(f"[API] ID convertido para UUID: {roleta_id}")
    
    # Verificar se a roleta existe
    roleta = data_source.db.roletas.find_one({'id': roleta_id}, {'_id': 0})
    if not roleta:
        print(f"[API] Roleta não encontrada pelo ID: {roleta_id}")
        return jsonify({'error': 'Roleta não encontrada'}), 404
    
    print(f"[API] Roleta encontrada: {roleta['nome']}")
    
    # Obter os números da roleta
    numeros_brutos = data_source.obter_ultimos_numeros(roleta_id, limite)
    print(f"[API] Números brutos obtidos: {len(numeros_brutos)}")
    
    # Converter para formato com mais informações
    numeros = []
    for i, num in enumerate(numeros_brutos):
        cor = data_source.obter_cor_numero(num)
        timestamp = data_source.obter_timestamp_numero(roleta_id, num, i)
        numeros.append({
            "numero": num,
            "cor": cor,
            "timestamp": timestamp
        })
    
    resposta = {
        "roleta_id": roleta_id,
        "roleta_nome": roleta['nome'],
        "numeros": numeros,
        "total": len(numeros)
    }
    
    print(f"[API] Resposta formatada para '{roleta['nome']}': {len(numeros)} números")
    return jsonify(resposta)

@app.route('/api/roletas/<roleta_id>/numeros', methods=['POST'])
def add_roleta_numero(roleta_id):
    """Adiciona um novo número para uma roleta específica"""
    # Verificar se o corpo da requisição é válido
    if not request.is_json:
        return jsonify({"error": "Corpo da requisição deve ser JSON"}), 400
    
    # Obter dados do corpo da requisição
    data = request.json
    
    # Validar dados
    if 'numero' not in data:
        return jsonify({"error": "Campo 'numero' é obrigatório"}), 400
    
    try:
        numero = int(data['numero'])
        if numero < 0 or numero > 36:
            return jsonify({"error": "Número deve estar entre 0 e 36"}), 400
    except ValueError:
        return jsonify({"error": "Número deve ser um inteiro"}), 400
    
    # Obter roleta pelo ID
    roleta = data_source.db.roletas.find_one({'id': roleta_id}, {'_id': 0})
    if not roleta:
        return jsonify({'error': 'Roleta não encontrada'}), 404
    
    # Determinar cor do número
    cor = data_source.obter_cor_numero(numero)
    
    # Inserir número
    timestamp = data.get('timestamp', datetime.now().isoformat())
    sucesso = data_source.inserir_numero(roleta_id, roleta['nome'], numero, cor, timestamp)
    
    if sucesso:
        # Notificar clientes SSE sobre o novo número
        event_manager.notify_clients({
            "type": "new_number",
            "roleta_id": roleta_id,
            "roleta_nome": roleta['nome'],
            "numero": numero,
            "cor": cor,
            "timestamp": timestamp
        })
        
        return jsonify({
            "success": True,
            "message": f"Número {numero} inserido com sucesso para roleta {roleta['nome']}",
            "roleta_id": roleta_id,
            "numero": numero,
            "cor": cor,
            "timestamp": timestamp
        })
    else:
        return jsonify({
            "success": False,
            "error": f"Falha ao inserir número {numero} para roleta {roleta['nome']}"
        }), 500

@app.route('/api/events')
def sse_stream():
    """Endpoint SSE para receber atualizações em tempo real"""
    def generate():
        # Registrar cliente e obter fila
        client_queue = event_manager.register_client()
        
        # Enviar cabeçalho SSE
        yield 'retry: 10000\n\n'
        
        try:
            # Obter eventos históricos
            history = event_manager.get_event_history(limit=10)
            for event in history:
                yield f'data: {json.dumps(event)}\n\n'
            
            # Esperar por novos eventos
            while True:
                try:
                    # Timeout para evitar bloqueio indefinido
                    event = client_queue.get(timeout=30)
                    
                    # Enviar evento para o cliente
                    yield f'data: {json.dumps(event)}\n\n'
                except queue.Empty:
                    # Se não houver eventos, enviar ping para manter a conexão viva
                    yield f'data: {json.dumps({"type": "ping", "timestamp": datetime.now().isoformat()})}\n\n'
        except:
            # Em caso de erro, remover cliente
            event_manager.unregister_client(client_queue)
        
        # Quando a conexão for fechada, remover cliente
        event_manager.unregister_client(client_queue)
    
    # Configurar cabeçalhos da resposta para SSE
    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['Connection'] = 'keep-alive'
    response.headers['X-Accel-Buffering'] = 'no'  # Para Nginx
    
    return response

@app.route('/api/test/event', methods=['POST'])
def test_event():
    """Endpoint para testar o envio de eventos SSE"""
    # Verificar se o corpo da requisição é válido
    if not request.is_json:
        return jsonify({"error": "Corpo da requisição deve ser JSON"}), 400
    
    # Obter dados do corpo da requisição
    data = request.json
    
    # Validar dados
    if 'type' not in data:
        return jsonify({"error": "Campo 'type' é obrigatório"}), 400
    
    # Adicionar timestamp se não existir
    if 'timestamp' not in data:
        data['timestamp'] = datetime.now().isoformat()
    
    # Notificar clientes SSE
    event_manager.notify_clients(data)
    
    return jsonify({
        "success": True,
        "message": "Evento enviado com sucesso",
        "event": data
    })

def start_server(host=DEFAULT_HOST, port=DEFAULT_PORT):
    """Inicia o servidor Flask"""
    # Exibir URLs de acesso
    print(f"\n🚀 API Backend: http://{host}:{port}")
    print(f"📱 Frontend Vercel: https://runcashnew-frontend-nu.vercel.app")
    print("\n📍 Endpoints disponíveis:")
    print(f"  • /api/status - Verifica se a API está online")
    print(f"  • /api/roletas - Lista todas as roletas")
    print(f"  • /api/roletas/:id - Detalhes de uma roleta")
    print(f"  • /api/roletas/:id/numeros - Números de uma roleta")
    print(f"  • /api/events - Conexão SSE para atualizações em tempo real\n")
    
    # Iniciar servidor
    app.run(host=host, port=port, threaded=True)

if __name__ == "__main__":
    start_server() 