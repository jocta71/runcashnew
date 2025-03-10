import time
import random
import re
import schedule
import json
import os
import platform
from datetime import datetime
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client
from flask import Flask, Response, request, jsonify
from flask_cors import CORS
import threading
import queue
import sys

from config import CASINO_URL, SUPABASE_URL, SUPABASE_KEY, roleta_permitida_por_id, SCRAPE_INTERVAL_MINUTES, logger, MAX_CICLOS
from strategy_analyzer import StrategyAnalyzer

# Verificar se estamos em ambiente de produção (Render, etc.)
IS_PRODUCTION = os.environ.get('RENDER', False) or os.environ.get('PRODUCTION', False)

# Criar a aplicação Flask
app = Flask(__name__)

# Configurar CORS - permitir requisições de qualquer origem em produção,
# ou apenas do localhost em desenvolvimento
if IS_PRODUCTION:
    # Em produção, permitir requisições apenas do domínio do frontend na Vercel
    # e outros domínios permitidos
    cors_origins = [
        "https://runcashnew.vercel.app",       # URL do seu frontend na Vercel
        "https://runcashnew-git-master-jocta71.vercel.app",
        "https://www.runcashnew.com",          # Se você tiver um domínio personalizado
        "http://localhost:5173",               # Para desenvolvimento local
        "http://localhost:3000"                # Alternativa para desenvolvimento
    ]
    CORS(app, resources={
        r"/*": {"origins": cors_origins, "supports_credentials": True}
    })
    logger.info(f"CORS configurado para origens específicas: {cors_origins}")
else:
    # Em desenvolvimento, permitir todas as origens
    CORS(app)
    logger.info("CORS configurado para permitir todas as origens (modo desenvolvimento)")

# Inicialização do cliente Supabase
# Garantir que a URL do Supabase esteja corretamente formatada
supabase_url = SUPABASE_URL
if supabase_url.startswith('@'):
    supabase_url = supabase_url[1:]
if not supabase_url.startswith('http'):
    supabase_url = f"https://{supabase_url}"

try:
    supabase = create_client(supabase_url, SUPABASE_KEY)
    logger.info(f"Cliente Supabase inicializado com sucesso: {supabase_url}")
except Exception as e:
    logger.error(f"Erro ao inicializar cliente Supabase: {str(e)}")
    logger.error(f"URL: {supabase_url}")
    logger.error(f"Key: {SUPABASE_KEY[:10]}...")

# Criando a classe EventManager para gerenciar eventos SSE
class EventManager:
    def __init__(self):
        self.clients = []
        self.event_queue = queue.Queue()
        
    def register_client(self, client_queue):
        self.clients.append(client_queue)
        logger.info(f"Novo cliente SSE registrado. Total: {len(self.clients)}")
        
    def unregister_client(self, client_queue):
        if client_queue in self.clients:
            self.clients.remove(client_queue)
            logger.info(f"Cliente SSE desconectado. Restantes: {len(self.clients)}")
    
    def notify_clients(self, event_data):
        # Adicionar evento à fila
        self.event_queue.put(event_data)
        logger.info(f"Evento adicionado à fila: {event_data.get('type')} - {event_data.get('roleta')} - {event_data.get('numero')}")
        
        # Enviar para todos os clientes
        for client_queue in self.clients[:]:  # Copia para evitar problemas se a lista mudar
            try:
                client_queue.put(event_data)
                logger.info(f"Evento enviado para um cliente")
            except Exception as e:
                logger.error(f"Erro ao enviar evento para cliente: {str(e)}")
                # Cliente com problema, remover
                self.unregister_client(client_queue)

# Instanciando o gerenciador de eventos
event_manager = EventManager()

@app.route('/events')
def sse():
    """Endpoint SSE para transmitir eventos de novos números de roletas em tempo real"""
    def generate():
        client_queue = queue.Queue()
        event_manager.register_client(client_queue)
        
        # Enviar um evento inicial
        initial_msg = json.dumps({"type": "connected", "message": "Conexão SSE estabelecida"})
        yield f'data: {initial_msg}\n\n'
        
        # Verificar se há eventos na fila do gerenciador para enviar imediatamente
        if not event_manager.event_queue.empty():
            try:
                # Enviar até 5 eventos recentes da fila, se houver
                for _ in range(5):
                    try:
                        event_data = event_manager.event_queue.get_nowait()
                        yield f'data: {json.dumps(event_data)}\n\n'
                        logger.info(f"Evento recente enviado para novo cliente: {event_data.get('type')}")
                    except queue.Empty:
                        break
            except Exception as e:
                logger.error(f"Erro ao enviar eventos recentes: {str(e)}")
        
        # Enviar evento de teste para confirmar a conexão
        test_event = {
            "type": "test_connection",
            "message": "Testando conexão SSE",
            "timestamp": time.time()
        }
        yield f'data: {json.dumps(test_event)}\n\n'
        
        try:
            while True:
                # Aguardar eventos na fila do cliente
                try:
                    event_data = client_queue.get(timeout=20)  # Reduzido para 20s para mais heartbeats
                    event_json = json.dumps(event_data)
                    logger.info(f"Enviando evento para cliente: {event_data.get('type')}")
                    yield f'data: {event_json}\n\n'
                except queue.Empty:
                    # Enviar heartbeat para manter a conexão viva
                    logger.debug("Enviando ping SSE para manter a conexão")
                    yield 'event: ping\ndata: {}\n\n'
        except GeneratorExit:
            # Cliente desconectou
            event_manager.unregister_client(client_queue)
            logger.info("Cliente desconectado do SSE")
    
    return Response(generate(), mimetype='text/event-stream', 
                   headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'})

# Endpoint de verificação de saúde para o Render
@app.route('/health')
def health_check():
    """Endpoint de verificação de saúde para monitoramento"""
    driver_status = "N/A"
    if hasattr(sys, 'scraper_thread_running'):
        driver_status = "Running" if sys.scraper_thread_running else "Not running"
    
    status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "scraper": driver_status,
        "clients_connected": len(event_manager.clients)
    }
    return jsonify(status)

@app.route('/api/test/event', methods=['POST'])
def generate_test_event():
    """Endpoint para gerar eventos de teste manualmente"""
    try:
        # Verificar autenticação (apenas para uso de desenvolvimento)
        if not IS_PRODUCTION or request.headers.get('X-API-Key') == os.environ.get('API_KEY'):
            data = request.json if request.is_json else {}
            
            # Usar os dados enviados ou gerar aleatórios
            roleta_nome = data.get('roleta', 'Roulette Live')
            numero = data.get('numero', random.randint(0, 36))
            roleta_id = data.get('roleta_id', '7x0b1tgh7agmf6hv')
            
            logger.info(f"[TESTE] Gerando evento manual para {roleta_nome} com número {numero}")
            
            # Criar o evento
            event_data = {
                "type": "new_number",
                "roleta": roleta_nome,
                "numero": numero,
                "timestamp": time.time(),
                "simulado": True,
                "manual": True,
                "test": True
            }
            
            # Inserir no Supabase
            try:
                inserir_novo_numero(roleta_id, roleta_nome, numero)
                logger.info(f"[TESTE] Número {numero} inserido no Supabase para {roleta_nome}")
            except Exception as e:
                logger.error(f"[TESTE] Erro ao inserir número simulado no Supabase: {str(e)}")
            
            # Verificar se há clientes conectados
            if len(event_manager.clients) > 0:
                logger.info(f"[TESTE] Notificando {len(event_manager.clients)} clientes sobre novo número")
                
                # Notificar clientes diretamente
                for client_queue in event_manager.clients[:]:
                    try:
                        client_queue.put(event_data)
                        logger.info(f"[TESTE] Evento enviado para um cliente")
                    except Exception as e:
                        logger.error(f"[TESTE] Erro ao enviar evento para cliente: {str(e)}")
                        # Cliente com problema, remover
                        event_manager.unregister_client(client_queue)
                
                # Também notificar via gerenciador de eventos (redundante, mas para garantir)
                event_manager.notify_clients(event_data)
            else:
                logger.warning("[TESTE] Nenhum cliente conectado para receber o evento")
            
            return jsonify({"success": True, "message": "Evento simulado enviado", "data": event_data})
        else:
            return jsonify({"success": False, "message": "Não autorizado"}), 401
    except Exception as e:
        logger.error(f"Erro ao gerar evento de teste: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500

# Endpoint para ver as roletas ativas atualmente
@app.route('/api/roletas')
def listar_roletas():
    try:
        response = supabase.table("roleta_numeros").select("roleta_nome").execute()
        roletas = []
        if response.data:
            # Extrair nomes únicos de roletas
            nomes = set([item['roleta_nome'] for item in response.data])
            roletas = list(nomes)
        
        return jsonify({
            "status": "success",
            "count": len(roletas),
            "roletas": roletas
        })
    except Exception as e:
        logger.error(f"Erro ao listar roletas: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

# Dicionário global para manter os analisadores de cada mesa
analisadores_mesas = {}

def configurar_driver():
    """Configura o driver do Selenium com opções para ambiente de cloud"""
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Versão mais recente do modo headless
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # Configurações adicionais específicas para o Render e ambientes cloud
    if IS_PRODUCTION:
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-setuid-sandbox")
        chrome_options.add_argument("--remote-debugging-port=9222")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36")
        
        # Caminhos possíveis para o Chrome/Chromium no Render
        chrome_paths = [
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
            "/usr/bin/chrome",
        ]
        
        # Tentar cada caminho possível
        for chrome_path in chrome_paths:
            try:
                if os.path.exists(chrome_path):
                    logger.info(f"Chrome encontrado em: {chrome_path}")
                    service = Service(chrome_path)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Driver do Chrome inicializado com caminho explícito em produção")
                    return driver
            except Exception as e:
                logger.warning(f"Erro ao inicializar Chrome com {chrome_path}: {str(e)}")
    
    # Método padrão para desenvolvimento local ou fallback
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        logger.info("Driver do Chrome inicializado com ChromeDriverManager")
        return driver
    except Exception as e:
        logger.error(f"Erro ao configurar o driver com ChromeDriverManager: {str(e)}")
        # Tentar ainda outro método em último caso
        try:
            driver = webdriver.Chrome(options=chrome_options)
            logger.info("Driver do Chrome inicializado com método de fallback")
            return driver
        except Exception as final_e:
            logger.critical(f"Falha em todos os métodos de inicialização do Chrome: {str(final_e)}")
            raise

def extrair_numeros_js(driver, elemento_roleta):
    """
    Extrai apenas o número mais recente (no topo) da roleta.
    
    Na interface do cassino, os números mais recentes geralmente aparecem primeiro/no topo,
    portanto vamos garantir que mantemos essa ordem ao extrair.
    """
    try:
        # Método 1: Procurar em spans dentro do elemento de informações e pegar apenas o primeiro (mais recente)
        numeros_elementos = elemento_roleta.find_elements(By.CSS_SELECTOR, ".cy-live-casino-grid-item-infobar-draws span")
        if numeros_elementos and len(numeros_elementos) > 0:
            numero_topo = numeros_elementos[0].text.strip()
            if numero_topo:
                logger.info(f"Número extraído (método 1): {numero_topo}")
                return [numero_topo]  # Retorna como lista com um único elemento
        
        # Método 2: Procurar em divs e pegar apenas o primeiro (mais recente)
        numeros_elementos = elemento_roleta.find_elements(By.CSS_SELECTOR, ".cy-live-casino-grid-item-infobar-draws div")
        if numeros_elementos and len(numeros_elementos) > 0:
            numero_topo = numeros_elementos[0].text.strip()
            if numero_topo:
                logger.info(f"Número extraído (método 2): {numero_topo}")
                return [numero_topo]  # Retorna como lista com um único elemento
        
        # Método 3: Extrair do texto completo usando regex e pegar apenas o primeiro número encontrado
        info_bar = elemento_roleta.find_element(By.CSS_SELECTOR, ".cy-live-casino-grid-item-infobar")
        if info_bar:
            texto_completo = info_bar.text
            # Padrão para encontrar números de 0 a 36
            numeros = re.findall(r'\b([0-9]|[1-2][0-9]|3[0-6])\b', texto_completo)
            if numeros and len(numeros) > 0:
                logger.info(f"Número extraído (método 3): {numeros[0]}")
                return [numeros[0]]  # Retorna apenas o primeiro número encontrado
    
    except (NoSuchElementException, Exception) as e:
        logger.warning(f"Erro ao extrair números: {str(e)}")
    
    logger.warning("Nenhum número encontrado para esta roleta")
    return []

def extrair_id_roleta(elemento_roleta):
    """Extrai o ID único da roleta a partir das classes do elemento"""
    try:
        classes = elemento_roleta.get_attribute("class")
        
        # Padrão 1: cy-live-casino-grid-item-123456
        match = re.search(r'cy-live-casino-grid-item-(\d+)', classes)
        if match:
            id_roleta = match.group(1)
            logger.info(f"ID da roleta extraído: {id_roleta}")
            return id_roleta
        
        # ID padrão usando o texto do título se não encontrar ID específico
        titulo = elemento_roleta.find_element(By.CSS_SELECTOR, ".cy-live-casino-grid-item-title").text
        id_hash = f"unknown-{hash(titulo) % 10000}"
        return id_hash
    
    except Exception as e:
        logger.warning(f"Erro ao extrair ID da roleta: {str(e)}")
        return "unknown"

def obter_ultimos_numeros(roleta_id, limite=1000):
    """
    Obtém os últimos números de uma roleta específica da tabela roleta_numeros
    """
    try:
        url = f"{supabase_url}/rest/v1/roleta_numeros"
        
        logger.info(f"Consultando números para roleta {roleta_id} em: {url}")
        
        response = supabase.table("roleta_numeros") \
            .select("numero") \
            .filter("roleta_id", "eq", roleta_id) \
            .order("created_at", desc=True) \
            .limit(limite) \
            .execute()
        
        if response.data:
            # Extrair apenas os números e converter para lista
            numeros = [item['numero'] for item in response.data]
            logger.info(f"Obtidos {len(numeros)} números para a roleta ID {roleta_id}")
            return numeros
        else:
            logger.info(f"Nenhum número encontrado para a roleta ID {roleta_id}")
            return []
    except Exception as e:
        logger.error(f"Erro ao obter números da roleta {roleta_id}: {str(e)}")
        return []

def inserir_novo_numero(roleta_id, roleta_nome, numero):
    """
    Insere um novo número na tabela roleta_numeros
    """
    try:
        # Validar o número
        if isinstance(numero, str):
            numero_int = int(re.sub(r'[^\d]', '', numero))
        else:
            numero_int = int(numero)
        
        if not (0 <= numero_int <= 36):
            logger.warning(f"Número inválido para inserção: {numero}")
            return False
        
        # Preparar dados para inserção
        data = {
            "roleta_id": roleta_id,
            "roleta_nome": roleta_nome,
            "numero": numero_int,
            "created_at": datetime.now().isoformat()
        }
        
        url = f"{supabase_url}/rest/v1/roleta_numeros"
        logger.info(f"Inserindo número {numero_int} para roleta {roleta_nome} em: {url}")
        
        # Inserir na tabela roleta_numeros
        response = supabase.table("roleta_numeros").insert(data).execute()
        logger.info(f"Número {numero_int} inserido para a roleta {roleta_nome} (ID: {roleta_id})")
        
        # Notificar clientes SSE sobre o novo número
        event_data = {
            "type": "new_number",
            "roleta_id": roleta_id,
            "roleta_nome": roleta_nome, 
            "numero": numero_int,
            "timestamp": datetime.now().isoformat()
        }
        event_manager.notify_clients(event_data)
        logger.info(f"Evento SSE enviado para novo número {numero_int} da roleta {roleta_nome}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao inserir número {numero} para a roleta {roleta_nome}: {str(e)}")
        return False

def processar_novos_numeros(roleta_id, roleta_nome, numeros_novos):
    """
    Processa novos números detectados para uma roleta
    """
    if not numeros_novos:
        return False
    
    # Obter números existentes para verificar duplicidade
    numeros_existentes = obter_ultimos_numeros(roleta_id, limite=100)
    
    # Verificar cada número novo
    numeros_adicionados = False
    for num_str in numeros_novos:
        try:
            # Validar o número
            if isinstance(num_str, str):
                num_limpo = re.sub(r'[^\d]', '', num_str)
                if not num_limpo:
                    continue
                num = int(num_limpo)
            else:
                num = int(num_str)
            
            # Verificar duplicidade (apenas com os mais recentes para performance)
            if not numeros_existentes or num != numeros_existentes[0]:
                if inserir_novo_numero(roleta_id, roleta_nome, num):
                    numeros_adicionados = True
                    # Atualizar a lista de números existentes
                    numeros_existentes.insert(0, num)
            else:
                logger.debug(f"Número {num} já existente para a roleta {roleta_nome}")
        except Exception as e:
            logger.warning(f"Erro ao processar número {num_str}: {str(e)}")
    
    return numeros_adicionados

def atualizar_dados_estrategia(roleta_id, roleta_nome, dados_estrategia):
    """
    Atualiza os dados de estratégia para uma roleta
    """
    try:
        # Verificamos se existe uma tabela auxiliar para dados de estratégia
        # Se não existe, podemos considerar criar uma no futuro
        logger.debug(f"Dados de estratégia processados para {roleta_nome}")
        # Por enquanto, apenas retornamos True pois não estamos armazenando esses dados
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar dados de estratégia para {roleta_nome}: {str(e)}")
        return False

def scrape_roletas(driver=None):
    """Função principal que realiza o scraping das roletas"""
    try:
        # Inicializar driver se não fornecido
        driver_interno = driver
        if driver_interno is None:
            try:
                driver_interno = configurar_driver()
            except Exception as e:
                logger.error(f"Erro ao configurar driver: {str(e)}")
                return None
        
        logger.info(f"Navegando para: {CASINO_URL}")
        driver_interno.get(CASINO_URL)
        
        # Aguardar carregamento da página (5-10 segundos)
        time.sleep(random.uniform(5, 10))
        
        # Iniciar ciclo de scraping
        ciclo = 1
        while ciclo <= MAX_CICLOS or MAX_CICLOS == 0:
            logger.info(f"Iniciando ciclo {ciclo} de scraping")
            
            # Encontrar todas as roletas na página
            elementos_roletas = driver_interno.find_elements(By.CSS_SELECTOR, ".cy-live-casino-grid-item")
            logger.info(f"Encontradas {len(elementos_roletas)} roletas na página")
            
            # Lista para armazenar roletas permitidas encontradas neste ciclo
            roletas_encontradas = []
            
            # Processar cada roleta
            for elemento_roleta in elementos_roletas:
                try:
                    # Extrair ID da roleta primeiro para filtrar rapidamente
                    id_roleta = extrair_id_roleta(elemento_roleta)
                    
                    # Verificar se a roleta está na lista de permitidas
                    if not roleta_permitida_por_id(id_roleta):
                        logger.debug(f"Roleta com ID {id_roleta} ignorada (não está na lista de permitidas)")
                        continue
                    
                    # Extrair título da roleta apenas para roletas permitidas
                    titulo_elemento = elemento_roleta.find_element(By.CSS_SELECTOR, ".cy-live-casino-grid-item-title")
                    titulo_roleta = titulo_elemento.text.strip()
                    
                    roletas_encontradas.append(f"{titulo_roleta} (ID: {id_roleta})")
                    logger.info(f"Processando roleta permitida: {titulo_roleta} (ID: {id_roleta})")
                    
                    # Inicializar analisador para a roleta se não existir
                    if titulo_roleta not in analisadores_mesas:
                        analisadores_mesas[titulo_roleta] = StrategyAnalyzer(titulo_roleta)
                        # Carregar números existentes no analisador
                        numeros_existentes = obter_ultimos_numeros(id_roleta)
                        if numeros_existentes:
                            analisadores_mesas[titulo_roleta].add_numbers(numeros_existentes)
                            logger.info(f"Carregados {len(numeros_existentes)} números existentes para o analisador de {titulo_roleta}")
                    
                    # Extrair números da roleta
                    numeros = extrair_numeros_js(driver_interno, elemento_roleta)
                    
                    # Processar novos números
                    if processar_novos_numeros(id_roleta, titulo_roleta, numeros):
                        logger.info(f"Novos números processados para {titulo_roleta}: {numeros}")
                    
                    # Adicionar números ao analisador
                    if analisadores_mesas[titulo_roleta].add_numbers(numeros):
                        logger.info(f"Novos números adicionados ao analisador para {titulo_roleta}: {numeros}")
                        
                        # Atualizar dados de estratégia se necessário
                        dados_estrategia = analisadores_mesas[titulo_roleta].get_data().get("estrategia", {})
                        atualizar_dados_estrategia(id_roleta, titulo_roleta, dados_estrategia)
                
                except Exception as e:
                    logger.error(f"Erro ao processar roleta: {str(e)}")
            
            # Registrar as roletas permitidas encontradas neste ciclo
            if roletas_encontradas:
                logger.info(f"Roletas permitidas encontradas neste ciclo: {len(roletas_encontradas)}")
                for roleta in roletas_encontradas:
                    logger.info(f"  - {roleta}")
            else:
                logger.warning("Nenhuma roleta permitida encontrada neste ciclo")
            
            # Pausa entre ciclos (entre 2 e 3 segundos)
            pausa = random.uniform(2, 3)
            time.sleep(pausa)
            
            # Incrementar ciclo apenas se MAX_CICLOS não for 0 (infinito)
            if MAX_CICLOS != 0:
                ciclo += 1
            else:
                logger.info(f"Ciclo {ciclo} completado, continuando indefinidamente...")
                ciclo += 1
    
    except Exception as e:
        logger.error(f"Erro no processo de scraping: {str(e)}")
    
    finally:
        # Fechar o driver apenas se foi criado internamente
        if driver is None and 'driver_interno' in locals() and driver_interno:
            try:
                driver_interno.quit()
                logger.info("Driver fechado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao fechar driver: {str(e)}")

# Função para simular dados quando o scraper não funcionar
def simulate_roulette_data():
    """Simula dados de roleta para testes quando o scraper não funciona"""
    logger.info("Iniciando simulação de dados de roleta para testes")
    
    # IDs e nomes de roletas comuns para simulação
    roletas_simuladas = [
        {"id": "vctlz3AoNaGCzxJi", "nome": "Auto-Roulette"},
        {"id": "LightningTable01", "nome": "Lightning Roulette"},
        {"id": "7x0b1tgh7agmf6hv", "nome": "Roulette Live"}
    ]
    
    # Gerar um evento inicial para confirmar que o simulador está funcionando
    try:
        roleta = roletas_simuladas[0]
        numero = random.randint(0, 36)
        logger.info(f"[SIMULAÇÃO] Gerando evento inicial com número {numero} para {roleta['nome']}")
        
        # Criar evento e notificar clientes
        event_data = {
            "type": "new_number",
            "roleta": roleta['nome'],
            "numero": numero,
            "timestamp": time.time(),
            "simulado": True,
            "startup": True
        }
        
        # Notificar clientes de forma mais direta
        for client_queue in event_manager.clients[:]:
            try:
                client_queue.put(event_data)
                logger.info(f"[SIMULAÇÃO] Evento inicial enviado para um cliente")
            except Exception as e:
                logger.error(f"[SIMULAÇÃO] Erro ao enviar evento inicial para cliente: {str(e)}")
        
        logger.info(f"[SIMULAÇÃO] Evento inicial enviado para {len(event_manager.clients)} clientes")
    except Exception as e:
        logger.error(f"[SIMULAÇÃO] Erro ao gerar evento inicial: {str(e)}")
    
    # Pequena pausa antes de iniciar o ciclo principal
    time.sleep(5)
    
    # Ciclo principal de simulação
    while True:
        try:
            # Selecionar uma roleta aleatória
            roleta = random.choice(roletas_simuladas)
            roleta_id = roleta["id"]
            roleta_nome = roleta["nome"]
            
            # Gerar número aleatório (0-36)
            numero = random.randint(0, 36)
            
            # Registrar log
            logger.info(f"[SIMULAÇÃO] Novo número: {numero} para {roleta_nome} (ID: {roleta_id})")
            
            # Inserir no Supabase
            try:
                inserir_novo_numero(roleta_id, roleta_nome, numero)
                logger.info(f"[SIMULAÇÃO] Número {numero} inserido no Supabase para {roleta_nome}")
            except Exception as e:
                logger.error(f"[SIMULAÇÃO] Erro ao inserir número simulado: {str(e)}")
            
            # Notificar clientes
            event_data = {
                "type": "new_number",
                "roleta": roleta_nome,
                "numero": numero,
                "timestamp": time.time(),
                "simulado": True
            }
            
            # Verificar se há clientes conectados
            if len(event_manager.clients) > 0:
                logger.info(f"[SIMULAÇÃO] Notificando {len(event_manager.clients)} clientes sobre novo número")
                event_manager.notify_clients(event_data)
            else:
                logger.warning("[SIMULAÇÃO] Nenhum cliente conectado para receber o evento")
            
            # Aguardar intervalo mais curto para testes (10-30 segundos)
            intervalo = random.randint(10, 30)
            logger.info(f"[SIMULAÇÃO] Aguardando {intervalo} segundos até o próximo número")
            time.sleep(intervalo)
            
        except Exception as e:
            logger.error(f"[SIMULAÇÃO] Erro ao simular dados: {str(e)}")
            time.sleep(10)  # Aguardar e tentar novamente

def main():
    """Função principal"""
    try:
        # Verificar se a tabela roleta_numeros existe
        try:
            supabase.table("roleta_numeros").select("count").limit(1).execute()
            logger.info("Tabela roleta_numeros verificada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao verificar tabela roleta_numeros: {str(e)}")
            logger.warning("A tabela pode não existir ou há um problema de conexão")
        
        # Se estivermos em produção e a simulação estiver ativada
        if IS_PRODUCTION and os.environ.get('SIMULATE_DATA') == 'true':
            logger.info("Modo de simulação de dados ativado")
            simulate_roulette_data()
            return
        
        # Se estivermos em produção e em ambiente cloud como o Render, 
        # pode ser necessário desabilitar o scraping com Selenium
        if IS_PRODUCTION and os.environ.get('DISABLE_SCRAPER') == 'true':
            logger.warning("Scraper desabilitado em ambiente de produção por configuração")
            return
            
        # Iniciar o scraping
        scrape_roletas()
        
    except Exception as e:
        logger.error(f"Erro na função principal: {str(e)}")

if __name__ == "__main__":
    # Marcar a thread do scraper como iniciada
    sys.scraper_thread_running = False
    
    # Iniciar o scraper em um thread separado
    if not os.environ.get('FLASK_ENV') == 'development' and not os.environ.get('DISABLE_SCRAPER') == 'true':
        if os.environ.get('SIMULATE_DATA') == 'true':
            logger.info("Iniciando simulador de dados em thread separada")
            # Iniciar o simulador diretamente em vez de através da função main
            simulator_thread = threading.Thread(target=simulate_roulette_data)
            simulator_thread.daemon = True
            simulator_thread.start()
            sys.scraper_thread_running = True
            logger.info("Thread do simulador iniciada com sucesso")
        else:
            scraper_thread = threading.Thread(target=main)
            scraper_thread.daemon = True
            scraper_thread.start()
            sys.scraper_thread_running = True
            logger.info("Scraper iniciado em thread separada")
    else:
        logger.info("Scraper não iniciado automaticamente (modo desenvolvimento ou desabilitado)")
    
    # Iniciar o servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
