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
import traceback
import psutil
from selenium.webdriver.common.action_chains import ActionChains

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

# Variáveis globais para monitoramento
ultima_extracao_bem_sucedida = None
contagem_extrações = 0
contagem_erros = 0
status_scraper = "inactive"
inicio_scraper = None

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
    """Extrai os números da roleta usando JavaScript"""
    global ultima_extracao_bem_sucedida, contagem_extrações, contagem_erros
    
    try:
        # Implementação existente...
        # Passar o mouse sobre o elemento para ativar possíveis tooltips
        actions = ActionChains(driver)
        actions.move_to_element(elemento_roleta).perform()
        
        # Capturar a lista de números usando JavaScript
        script = """
        function extrairNumeros(elemento) {
            // Buscar números dentro do elemento passando pelo shadow DOM
            const container = elemento.querySelector('.tile-body') || elemento;
            const numerosElem = container.querySelectorAll('.roulette-historytool');
            const numeros = [];
            
            if (numerosElem && numerosElem.length > 0) {
                numerosElem.forEach(e => {
                    const texto = e.textContent.trim();
                    const numero = parseInt(texto);
                    if (!isNaN(numero)) {
                        numeros.push(numero);
                    }
                });
                return numeros;
            }

            // Se não encontrou pela classe específica, tenta encontrar pelo texto
            const todosElementos = container.querySelectorAll('*');
            for (const elem of todosElementos) {
                const texto = elem.textContent.trim();
                const numero = parseInt(texto);
                if (!isNaN(numero) && numero >= 0 && numero <= 36) {
                    numeros.push(numero);
                }
            }
            
            return numeros;
        }
        return extrairNumeros(arguments[0]);
        """
        numeros = driver.execute_script(script, elemento_roleta)
        
        # Registrar tentativa bem-sucedida
        ultima_extracao_bem_sucedida = datetime.now().isoformat()
        contagem_extrações += 1
        
        return numeros
    except Exception as e:
        # Registrar erro
        contagem_erros += 1
        logger.error(f"Erro ao extrair números com JavaScript: {str(e)}")
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
    """Processa novos números obtidos da roleta"""
    global ultima_extracao_bem_sucedida
    
    if not numeros_novos:
        return []
    
    logger.info(f"Processando {len(numeros_novos)} números novos para {roleta_nome}")
    
    # Obter os números já salvos desta roleta
    ultimos_numeros = obter_ultimos_numeros(roleta_id)
    
    # Filtrar apenas os números que ainda não foram salvos
    numeros_a_inserir = []
    for numero in numeros_novos:
        # Verificar se este número não está entre os últimos salvos
        if numero not in ultimos_numeros:
            numeros_a_inserir.append(numero)
    
    # Se tiver números novos, inseri-los no banco
    if numeros_a_inserir:
        logger.info(f"Inserindo {len(numeros_a_inserir)} números novos para {roleta_nome}: {numeros_a_inserir}")
        for numero in numeros_a_inserir:
            inserir_novo_numero(roleta_id, roleta_nome, numero)
            
            # Atualizar timestamp da última extração bem-sucedida
            ultima_extracao_bem_sucedida = datetime.now().isoformat()
            
    else:
        logger.info(f"Nenhum número novo para inserir para {roleta_nome}")
    
    return numeros_a_inserir

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
    """Função principal de scraping"""
    try:
        # Inicializar contador de ciclos e tempo de execução
        ciclo_atual = 0
        tempo_inicio = time.time()
        ultima_reinicializacao_driver = tempo_inicio
        driver_interno = False
        
        # Log de início da execução
        logger.info(f"Iniciando scraping de roletas. Tempo máximo de ciclos: {MAX_CICLOS}")
        
        while True:
            try:
                # Verificar se atingimos o limite de ciclos (0 = sem limite)
                if MAX_CICLOS > 0 and ciclo_atual >= MAX_CICLOS:
                    logger.info(f"Atingido limite de {MAX_CICLOS} ciclos. Finalizando.")
                    break
                
                # Verificar se é necessário reinicializar o driver (a cada 2 horas)
                tempo_atual = time.time()
                if tempo_atual - ultima_reinicializacao_driver > 7200:  # 2 horas em segundos
                    logger.info("Reinicializando driver após 2 horas de execução para prevenir problemas de memória")
                    if driver_interno and driver:
                        try:
                            driver.quit()
                        except Exception as e:
                            logger.error(f"Erro ao fechar driver antigo: {str(e)}")
                    
                    driver = configurar_driver()
                    driver_interno = True
                    ultima_reinicializacao_driver = tempo_atual
                    logger.info("Driver reinicializado com sucesso")
                
                # Se não temos um driver, criar um
                if not driver:
                    logger.info("Driver não fornecido, configurando um novo")
                    driver = configurar_driver()
                    driver_interno = True
                
                ciclo_atual += 1
                logger.info(f"Iniciando ciclo {ciclo_atual}")
                
                # Encontrar todas as roletas na página
                elementos_roletas = driver.find_elements(By.CSS_SELECTOR, ".cy-live-casino-grid-item")
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
                        numeros = extrair_numeros_js(driver, elemento_roleta)
                        
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
                
                # Adicionar verificação de saúde periódica
                if ciclo_atual % 5 == 0:  # A cada 5 ciclos
                    logger.info(f"Verificação de saúde: Scraper funcionando há {round((time.time() - tempo_inicio) / 60, 2)} minutos, {ciclo_atual} ciclos executados")
                
                # Pausa entre ciclos para não sobrecarregar o site alvo
                time.sleep(SCRAPE_INTERVAL_MINUTES * 60)
                
            except Exception as e:
                logger.error(f"Erro durante o ciclo {ciclo_atual}: {str(e)}")
                logger.error(f"Stacktrace: {traceback.format_exc()}")
                
                # Tentar recuperar de erros
                try:
                    if driver:
                        # Verificar se o driver ainda está respondendo
                        try:
                            # Tente acessar uma propriedade simples
                            _ = driver.current_url
                        except:
                            logger.error("Driver não está respondendo. Reinicializando...")
                            try:
                                driver.quit()
                            except:
                                logger.error("Não foi possível fechar o driver antigo")
                            
                            driver = configurar_driver()
                            driver_interno = True
                except Exception as recovery_error:
                    logger.error(f"Erro durante tentativa de recuperação: {str(recovery_error)}")
                
                # Pausa mais longa após erro para evitar sobrecarga
                logger.info("Aguardando 2 minutos antes de tentar novamente após erro")
                time.sleep(120)
        
        # Fechar o driver se foi criado internamente
        if driver_interno and driver:
            try:
                driver.quit()
                logger.info("Driver fechado com sucesso")
            except Exception as e:
                logger.error(f"Erro ao fechar driver: {str(e)}")
    
    except Exception as e:
        logger.error(f"Erro crítico na função de scraping: {str(e)}")
        logger.error(f"Stacktrace: {traceback.format_exc()}")
        
        # Tentar fechar o driver se houver exceção crítica
        if driver_interno and driver:
            try:
                driver.quit()
            except:
                pass
        
        # Notificar administradores sobre falha crítica
        logger.critical("Falha crítica no scraper. Necessário verificar manualmente.")
        
        # Reiniciar o serviço após falha crítica (se estiver no modo de recuperação automática)
        if os.environ.get('AUTO_RECOVER', 'true').lower() == 'true':
            logger.info("Tentando reiniciar o serviço devido a falha crítica...")
            # Iniciar novo processo
            os.execv(sys.executable, ['python'] + sys.argv)

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
    time.sleep(1)  # Reduzido de 5 para 1 segundo
    
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
            
            # Intervalo ULTRA RÁPIDO (1-3 segundos)
            intervalo = random.randint(1, 3)
            logger.info(f"[SIMULAÇÃO] Aguardando {intervalo} segundos até o próximo número")
            time.sleep(intervalo)
            
        except Exception as e:
            logger.error(f"[SIMULAÇÃO] Erro ao simular dados: {str(e)}")
            time.sleep(5)  # Reduzido de 10 para 5 segundos

@app.route('/api/start-simulator', methods=['GET'])
def start_simulator():
    """Endpoint para iniciar manualmente o simulador de dados, para fins de diagnóstico"""
    try:
        # Verificar se já existe um simulador ativo
        if hasattr(sys, 'simulator_thread_running') and sys.simulator_thread_running:
            logger.info("Simulador já está ativo, gerando um novo evento de teste")
            
            # Gerar um evento de teste mesmo assim
            roleta_nome = "Lightning Roulette"
            numero = random.randint(0, 36)
            roleta_id = "LightningTable01"
            
            # Criar o evento
            event_data = {
                "type": "new_number",
                "roleta": roleta_nome,
                "numero": numero,
                "timestamp": time.time(),
                "simulado": True,
                "manual_trigger": True
            }
            
            # Notificar clientes
            if len(event_manager.clients) > 0:
                logger.info(f"[TESTE MANUAL] Notificando {len(event_manager.clients)} clientes sobre novo número")
                
                # Notificar diretamente
                for client_queue in event_manager.clients[:]:
                    try:
                        client_queue.put(event_data)
                        logger.info(f"[TESTE MANUAL] Evento enviado para um cliente")
                    except Exception as e:
                        logger.error(f"[TESTE MANUAL] Erro ao enviar evento para cliente: {str(e)}")
                
                # Também via gerenciador
                event_manager.notify_clients(event_data)
                
                return jsonify({
                    "success": True, 
                    "message": "Evento de teste enviado para o simulador existente",
                    "clients": len(event_manager.clients),
                    "data": event_data
                })
            else:
                return jsonify({
                    "success": False,
                    "message": "Simulador ativo mas não há clientes conectados",
                    "clients": 0
                })
        
        # Iniciar novo simulador se não existir
        simulator_thread = threading.Thread(target=simulate_roulette_data)
        simulator_thread.daemon = True
        simulator_thread.start()
        
        # Marcar como iniciado
        sys.simulator_thread_running = True
        logger.info("Simulador iniciado manualmente via endpoint")
        
        return jsonify({
            "success": True,
            "message": "Simulador iniciado com sucesso",
            "clients": len(event_manager.clients)
        })
    
    except Exception as e:
        logger.error(f"Erro ao iniciar simulador manualmente: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erro: {str(e)}"
        }), 500

# Função para forçar um evento único simulado
@app.route('/api/force-event', methods=['GET'])
def force_event():
    """Endpoint para forçar a geração de um evento simulado imediatamente"""
    try:
        # Selecionar roleta e número aleatório
        roletas_simuladas = [
            {"id": "vctlz3AoNaGCzxJi", "nome": "Auto-Roulette"},
            {"id": "LightningTable01", "nome": "Lightning Roulette"},
            {"id": "7x0b1tgh7agmf6hv", "nome": "Roulette Live"}
        ]
        
        roleta = random.choice(roletas_simuladas)
        roleta_id = roleta["id"]
        roleta_nome = roleta["nome"]
        numero = random.randint(0, 36)
        
        # Criar evento
        event_data = {
            "type": "new_number",
            "roleta": roleta_nome,
            "numero": numero,
            "timestamp": time.time(),
            "simulado": True,
            "forced": True
        }
        
        # Inserir no Supabase
        try:
            inserir_novo_numero(roleta_id, roleta_nome, numero)
            logger.info(f"[EVENTO FORÇADO] Número {numero} inserido no Supabase para {roleta_nome}")
        except Exception as e:
            logger.error(f"[EVENTO FORÇADO] Erro ao inserir no Supabase: {str(e)}")
        
        # Verificar clientes conectados
        if len(event_manager.clients) > 0:
            # Envio direto para garantir a entrega
            for client_queue in event_manager.clients[:]:
                try:
                    client_queue.put(event_data)
                    logger.info(f"[EVENTO FORÇADO] Enviado para um cliente")
                except Exception as e:
                    logger.error(f"[EVENTO FORÇADO] Erro ao enviar: {str(e)}")
            
            # Envio via gerenciador
            event_manager.notify_clients(event_data)
            
            return jsonify({
                "success": True,
                "message": f"Evento forçado: {numero} em {roleta_nome}",
                "clients": len(event_manager.clients),
                "data": event_data
            })
        else:
            return jsonify({
                "success": False,
                "message": "Evento gerado mas não há clientes conectados",
                "data": event_data,
                "clients": 0
            })
    
    except Exception as e:
        logger.error(f"Erro ao forçar evento: {str(e)}")
        return jsonify({
            "success": False,
            "message": f"Erro: {str(e)}"
        }), 500

@app.route('/api/status', methods=['GET'])
def get_status():
    """Retorna informações sobre o status do sistema"""
    try:
        # Calcular tempo de atividade
        uptime = None
        if inicio_scraper:
            uptime_seconds = time.time() - inicio_scraper
            uptime = {
                "seconds": int(uptime_seconds),
                "minutes": int(uptime_seconds / 60),
                "hours": int(uptime_seconds / 3600),
                "days": int(uptime_seconds / 86400)
            }
        
        # Obter estatísticas
        status = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "clients_connected": len(event_manager.clients),
            "scraper": status_scraper,
            "last_successful_extraction": ultima_extracao_bem_sucedida,
            "extraction_count": contagem_extrações,
            "error_count": contagem_erros,
            "uptime": uptime,
            "simulator_running": hasattr(sys, 'simulator_thread_running') and sys.simulator_thread_running,
            "memory_usage_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2) if 'psutil' in sys.modules else "N/A"
        }
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Erro ao obter status: {str(e)}")
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/restart-scraper', methods=['POST'])
def restart_scraper():
    """Endpoint para reiniciar o scraper remotamente"""
    try:
        logger.info("Reinicialização remota do scraper solicitada")
        
        # Verificar autorização através de uma chave secreta no cabeçalho
        auth_key = request.headers.get('X-API-KEY')
        if not auth_key or auth_key != os.environ.get('ADMIN_API_KEY', 'admin-secret-key'):
            logger.warning("Tentativa de reinicialização não autorizada do scraper")
            return jsonify({"error": "Não autorizado"}), 401
        
        # Iniciar thread para reiniciar o serviço (isso permite que o endpoint responda primeiro)
        def restart_service():
            time.sleep(1)  # Pequena pausa para garantir que a resposta da API seja enviada
            logger.info("Reiniciando o serviço...")
            os.execv(sys.executable, ['python'] + sys.argv)
        
        threading.Thread(target=restart_service).start()
        
        return jsonify({
            "message": "Reiniciando o serviço, por favor aguarde...",
            "status": "restarting"
        })
    except Exception as e:
        logger.error(f"Erro ao reiniciar scraper: {str(e)}")
        return jsonify({
            "error": str(e)
        }), 500

@app.route('/api/scraper/logs', methods=['GET'])
def get_scraper_logs():
    """Endpoint para obter os últimos logs do scraper"""
    try:
        # Verificar autorização através de uma chave secreta no cabeçalho
        auth_key = request.headers.get('X-API-KEY')
        if not auth_key or auth_key != os.environ.get('ADMIN_API_KEY', 'admin-secret-key'):
            logger.warning("Tentativa não autorizada de acessar logs")
            return jsonify({"error": "Não autorizado"}), 401
        
        # Obter parâmetros de consulta
        lines = request.args.get('lines', default=100, type=int)
        level = request.args.get('level', default='INFO').upper()
        
        # Limitar o número de linhas
        lines = min(lines, 1000)
        
        # Caminho para o arquivo de log (ajuste conforme sua configuração)
        log_file = os.environ.get('LOG_FILE', 'scraper.log')
        
        # Verificar se o arquivo existe
        if not os.path.exists(log_file):
            return jsonify({
                "error": f"Arquivo de log {log_file} não encontrado",
                "logs": []
            }), 404
        
        # Ler as últimas linhas do arquivo
        with open(log_file, 'r') as f:
            all_logs = f.readlines()
        
        # Filtrar por nível, se especificado
        if level != 'ALL':
            filtered_logs = [log for log in all_logs if level in log]
        else:
            filtered_logs = all_logs
        
        # Obter as últimas N linhas
        last_logs = filtered_logs[-lines:] if lines < len(filtered_logs) else filtered_logs
        
        return jsonify({
            "total_lines": len(all_logs),
            "filtered_lines": len(filtered_logs),
            "showing_lines": len(last_logs),
            "logs": last_logs
        })
    except Exception as e:
        logger.error(f"Erro ao obter logs: {str(e)}")
        return jsonify({
            "error": str(e)
        }), 500

def main():
    """Função principal"""
    global status_scraper, inicio_scraper
    
    try:
        # Inicializar variáveis de monitoramento
        inicio_scraper = time.time()
        status_scraper = "starting"
        
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
            status_scraper = "simulator_active"
            simulate_roulette_data()
            return
        
        # Se estivermos em produção e em ambiente cloud como o Render, 
        # pode ser necessário desabilitar o scraping com Selenium
        if IS_PRODUCTION and os.environ.get('DISABLE_SCRAPER') == 'true':
            logger.warning("Scraper desabilitado em ambiente de produção por configuração")
            status_scraper = "disabled"
            return
        
        # Iniciar o scraping
        status_scraper = "active"
        scrape_roletas()
        
    except Exception as e:
        logger.error(f"Erro na função principal: {str(e)}")
        status_scraper = "error"

if __name__ == "__main__":
    # Marcar a thread do scraper como iniciada
    sys.scraper_thread_running = False
    sys.simulator_thread_running = False
    
    # Forçar simulação se estiver configurada
    simulate_data = os.environ.get('SIMULATE_DATA') == 'true'
    disable_scraper = os.environ.get('DISABLE_SCRAPER') == 'true'
    is_dev = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Configuração: SIMULATE_DATA={simulate_data}, DISABLE_SCRAPER={disable_scraper}, DEV={is_dev}")
    
    # Iniciar o simulador em thread separado se estiver configurado
    if simulate_data and not is_dev:
        logger.info("Iniciando simulador de dados em thread separada (SIMULATE_DATA=true)")
        try:
            # Iniciar o simulador diretamente
            simulator_thread = threading.Thread(target=simulate_roulette_data)
            simulator_thread.daemon = True
            simulator_thread.start()
            sys.simulator_thread_running = True
            logger.info("Thread do simulador iniciada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao iniciar simulador: {str(e)}")
    
    # Iniciar o scraper se não estiver desabilitado e não estiver em modo de simulação
    if not disable_scraper and not simulate_data and not is_dev:
        logger.info("Iniciando scraper em thread separada")
        try:
            scraper_thread = threading.Thread(target=main)
            scraper_thread.daemon = True
            scraper_thread.start()
            sys.scraper_thread_running = True
            logger.info("Thread do scraper iniciada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao iniciar scraper: {str(e)}")
    
    # Inicializar um simulador de backup (10s) caso nenhum outro método tenha sido iniciado
    if not sys.simulator_thread_running and not sys.scraper_thread_running:
        logger.info("Iniciando simulador de backup após 10 segundos")
        
        def start_delayed_simulator():
            logger.info("Aguardando 10 segundos para iniciar simulador de backup...")
            time.sleep(10)
            logger.info("Iniciando simulador de backup")
            sys.simulator_thread_running = True
            simulate_roulette_data()
        
        backup_thread = threading.Thread(target=start_delayed_simulator)
        backup_thread.daemon = True
        backup_thread.start()
    
    # Iniciar o servidor Flask
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Iniciando servidor Flask na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
