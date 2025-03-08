import time
import random
import re
import json
import os
import platform
from datetime import datetime, timedelta
import logging
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from flask import Flask, render_template, jsonify
import threading
from strategy_analyzer import StrategyAnalyzer
from enum import Enum
from terminal_table import TERMINAL_TABLE
from config import SUPABASE_URL, SUPABASE_KEY, logger

# Determine if we're running on Railway
IS_RAILWAY = os.environ.get('RAILWAY_STATIC_URL') is not None or os.environ.get('RAILWAY_SERVICE_ID') is not None

# Only import Selenium if not on Railway
if not IS_RAILWAY:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

# Inicialização do cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('extrator.log')
    ]
)

app = Flask(__name__)

# Variáveis globais para armazenar dados
numeros_roletas = {}
driver = None
thread_extracao = None
executando = False

# Dicionário para armazenar os analisadores de cada mesa
analisadores_mesas = {}

class RouletteState(Enum):
    MORTO = "MORTO"
    NEUTRAL = "NEUTRAL"
    TRIGGER = "TRIGGER"
    GALE = "GALE"
    POST_GALE_NEUTRAL = "POST_GALE_NEUTRAL"

class RouletteStrategy:
    def __init__(self):
        self.current_state = RouletteState.NEUTRAL
        self.trigger_number = -1
        self.previous_trigger_number = -1
        self.result_processed = False
        self.win_count = 0
        self.loss_count = 0
        self.history = []
        self.terminal_table = TERMINAL_TABLE
        
    async def process_number(self, number):
        self.history.append(number)
        
        # Track old state for change detection
        old_state = self.current_state
        
        # Logging for debugging
        logging.info(f"Processing number: {number} | Current state: {self.current_state.value}")
        
        if self.current_state == RouletteState.MORTO:
            logging.info("State MORTO: Resetting to NEUTRAL")
            self.current_state = RouletteState.NEUTRAL
            self.result_processed = False
            
        elif self.current_state == RouletteState.NEUTRAL:
            self.trigger_number = number
            
            if self.trigger_number in self.terminal_table:
                terminals = self.terminal_table[self.trigger_number][:3]  # Get first 3 numbers
                terminals_str = ''.join(map(str, terminals))
                logging.info(f"Trigger number {self.trigger_number} found. Terminals: {terminals_str}")
                self.analyze_terminals(self.trigger_number)
            else:
                logging.warning(f"Trigger number {self.trigger_number} not found in table.")
                
            self.current_state = RouletteState.TRIGGER
            
        elif self.current_state == RouletteState.TRIGGER:
            if self.trigger_number not in self.terminal_table:
                return
                
            terminals = self.terminal_table[self.trigger_number]
            
            if number in terminals:
                logging.info("WIN!")
                self.process_result(True)
                self.current_state = RouletteState.MORTO
            else:
                logging.info("GALE!")
                self.previous_trigger_number = self.trigger_number
                self.current_state = RouletteState.POST_GALE_NEUTRAL
                
        elif self.current_state == RouletteState.POST_GALE_NEUTRAL:
            if self.previous_trigger_number not in self.terminal_table:
                return
                
            terminals = self.terminal_table[self.previous_trigger_number]
            
            if number in terminals:
                logging.info("WIN after GALE!")
                self.process_result(True)
            else:
                logging.info("LOSS after GALE!")
                self.process_result(False)
                
            self.current_state = RouletteState.MORTO
            
        # Log state changes to help with debugging
        if old_state != self.current_state:
            logging.info(f"State changed: {old_state.value} -> {self.current_state.value}")
            # Force update to ensure frontend receives the state change
            
    def process_result(self, is_win):
        """Process the result (win or loss)"""
        if is_win:
            self.win_count += 1
        else:
            self.loss_count += 1
        
        logging.info(f"Result processed: {'Win' if is_win else 'Loss'}")
        logging.info(f"Score: {self.win_count}W / {self.loss_count}L")
        
    def analyze_terminals(self, trigger_number):
        """Analyze terminals for the trigger number"""
        if trigger_number in self.terminal_table:
            terminals = self.terminal_table[trigger_number]
            logging.info(f"Analyzing terminals for {trigger_number}: {terminals}")
            return terminals
        return []
            
    def get_status(self):
        # Get terminals for current trigger number
        current_terminals = []
        terminals_sum = 0
        if self.trigger_number in self.terminal_table:
            current_terminals = self.terminal_table[self.trigger_number]
            terminals_sum = sum(current_terminals)
        
        # Get terminals for previous trigger number (if any)
        previous_terminals = []
        previous_terminals_sum = 0
        if self.previous_trigger_number in self.terminal_table:
            previous_terminals = self.terminal_table[self.previous_trigger_number]
            previous_terminals_sum = sum(previous_terminals)
        
        return {
            "estado": self.current_state.value,
            "numero_gatilho": self.trigger_number,
            "numero_gatilho_anterior": self.previous_trigger_number,
            "terminais_gatilho": current_terminals,
            "soma_terminais_gatilho": terminals_sum,
            "terminais_gatilho_anterior": previous_terminals,
            "soma_terminais_anterior": previous_terminals_sum,
            "vitorias": self.win_count,
            "derrotas": self.loss_count,
            "total_jogadas": len(self.history),
            "ultimos_numeros": self.history[-5:] if self.history else []
        }

# Adicionar à aplicação
app.strategy = StrategyAnalyzer()

# Função de User Agent mais realista com rotação controlada
def get_user_agent():
    """
    Retorna um user agent realista para evitar bloqueios.
    Esta NÃO é uma simulação de dados, apenas uma técnica necessária para obter acesso ao site.
    """
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
    ]
    # Usar o dia atual como índice para alternar user agents periodicamente sem aleatoriedade
    day_of_month = datetime.now().day
    index = day_of_month % len(user_agents)
    return user_agents[index]

def configurar_driver(tentativa=1, max_tentativas=3):
    if IS_RAILWAY:
        logger.warning("Selenium não é compatível com Railway. Usando método alternativo.")
        return None
        
    print("Configurando driver para ambiente local...")
    
    try:
        # Importações necessárias se não estiver no Railway
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        
        # Configurações para o Chrome
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"user-agent={get_user_agent()}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Configuração para ambiente local
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        
        logging.info(f"Driver configurado com sucesso para ambiente local!")
        return driver
        
    except Exception as e:
        logging.error(f"Erro ao configurar driver (tentativa {tentativa}): {str(e)}")
        if tentativa < max_tentativas:
            time.sleep(10)
            return configurar_driver(tentativa + 1, max_tentativas)
        else:
            raise Exception(f"Falha ao configurar driver após {max_tentativas} tentativas")

def navegar_para_site(driver, tentativa=1, max_tentativas=3):
    if IS_RAILWAY or driver is None:
        logger.warning("Navegação para o site não disponível no Railway ou driver não configurado.")
        return False
        
    try:
        # Configurar DNS e conexão
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Network.setBypassServiceWorker', {'bypass': True})
        
        # Configurar timeout mais longo para DNS
        driver.set_page_load_timeout(60)
        
        # Limpar cookies e cache
        driver.delete_all_cookies()
        driver.execute_cdp_cmd('Network.clearBrowserCache', {})
        driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
        
        # Usar apenas a URL principal onde todas as roletas estão disponíveis
        url = "https://es.888casino.com/live-casino/#filters=live-roulette"
        
        try:
            logger.info(f"Acessando URL única: {url}")
            driver.get(url)
            # Aguardar carregamento inicial com timeout maior
            WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            time.sleep(5)
            
            if "888casino" in driver.current_url and "live-casino" in driver.current_url:
                logging.info(f"Sucesso ao acessar: {url}")
                return True
            else:
                logging.error(f"Página carregada, mas URL não é a esperada: {driver.current_url}")
                return False
    except Exception as e:
            logging.error(f"Falha ao acessar {url}: {str(e)}")
            raise
        
    except Exception as e:
        logging.error(f"Erro ao navegar para o site (tentativa {tentativa}): {str(e)}")
        if tentativa < max_tentativas:
            time.sleep(10)
            return navegar_para_site(driver, tentativa + 1, max_tentativas)
        else:
            raise Exception(f"Falha ao acessar o site após {max_tentativas} tentativas")

def atualizar_supabase(dados_roletas):
    """Atualiza os dados no Supabase"""
    try:
        # Para cada roleta, atualizar os dados no Supabase
        for nome_roleta, dados in dados_roletas.items():
            numeros = dados.get("numeros", [])
            id_roleta = dados.get("id", "")
            
            # Extrair os dados da estratégia
            estrategia = dados.get("estrategia", {})
            vitorias = estrategia.get("vitorias", 0)
            derrotas = estrategia.get("derrotas", 0)
            estado = estrategia.get("estado", "NEUTRAL")
            numero_gatilho = estrategia.get("numero_gatilho", -1)
            numero_gatilho_anterior = estrategia.get("numero_gatilho_anterior", -1)
            terminais_gatilho = estrategia.get("terminais_gatilho", [])
            terminais_gatilho_anterior = estrategia.get("terminais_gatilho_anterior", [])
            sugestao_display = estrategia.get("sugestao_display", "")
            
            # Construir o objeto de dados compatível com a estrutura da tabela
            dados_para_insert = {
                "id": id_roleta,
                "nome": nome_roleta,
                "numeros": numeros,
                "updated_at": datetime.now().isoformat(),
                # Adicionar campos da estratégia
                "estado_estrategia": estado,
                "numero_gatilho": numero_gatilho,
                "numero_gatilho_anterior": numero_gatilho_anterior,
                "terminais_gatilho": terminais_gatilho[:3],  # Limitar a 3
                "terminais_gatilho_anterior": terminais_gatilho_anterior[:3],  # Limitar a 3
                "vitorias": vitorias,
                "derrotas": derrotas,
                "sugestao_display": sugestao_display
            }
            
            logger.info(f"Enviando dados para o Supabase - Roleta: {nome_roleta}")
            
            # Upsert os dados na tabela 'roletas'
            result = supabase.table("roletas").upsert(dados_para_insert).execute()
            
            # Verificar se houve erro
            if result.data:
                logger.info(f"Dados da roleta {nome_roleta} atualizados com sucesso")
            else:
                logger.error(f"Erro ao atualizar dados da roleta {nome_roleta}: {result.error}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao atualizar dados no Supabase: {str(e)}")
        return False

def extrair_dados_api():
    """
    Método alternativo para extração de dados usando requisições HTTP diretas
    Compatível com Railway (sem Selenium) - APENAS DADOS REAIS
    SEM SIMULAÇÃO DE DADOS - Apenas técnicas necessárias para acessar APIs protegidas
    """
    global numeros_roletas, analisadores_mesas, executando
    
    # Apenas a URL principal com todas as roletas
    url = "https://es.888casino.com/live-casino/#filters=live-roulette"
    
    # APIs diretas (atualizadas com novos endpoints e parâmetros)
    api_urls = [
        "https://www.888casino.es/api/casino/games/live",
        "https://es.888casino.com/api/games/categories/live-roulette",
        "https://es.888casino.com/api/casino/games/live/roulette",
        "https://casino.888.es/api/games/live/roulette/list",
        "https://www.888casino.es/api/games/live/roulette/list"
    ]
    
    # Fingerprint do navegador para evitar bloqueios - SEM SIMULAÇÃO DE DADOS
    browser_fingerprint = {
        "sec-ch-ua": '"Chromium";v="120", "Google Chrome";v="120", "Not=A?Brand";v="99"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "accept-language": "es-ES,es;q=0.9,en;q=0.8",
        "accept-encoding": "gzip, deflate, br",
        "connection": "keep-alive",
        "upgrade-insecure-requests": "1"
    }
    
    # Headers para simular um navegador real (necessário para acessar o site)
    headers = {
        'User-Agent': get_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'Referer': 'https://es.888casino.com/live-casino/',
        'sec-ch-ua': browser_fingerprint["sec-ch-ua"],
        'sec-ch-ua-mobile': browser_fingerprint["sec-ch-ua-mobile"],
        'sec-ch-ua-platform': browser_fingerprint["sec-ch-ua-platform"],
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-User': '?1',
        'Accept-Encoding': browser_fingerprint["accept-encoding"]
    }
    
    # Headers específicos para requisições JSON/API 
    json_headers = {
        'User-Agent': get_user_agent(),
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
        'Referer': 'https://es.888casino.com/live-casino/',
        'Origin': 'https://es.888casino.com',
        'sec-ch-ua': browser_fingerprint["sec-ch-ua"],
        'sec-ch-ua-mobile': browser_fingerprint["sec-ch-ua-mobile"],
        'sec-ch-ua-platform': browser_fingerprint["sec-ch-ua-platform"],
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'Accept-Encoding': browser_fingerprint["accept-encoding"],
        'Accept-Language': browser_fingerprint["accept-language"],
        'Connection': browser_fingerprint["connection"]
    }
    
    last_update_time = time.time()
    session = requests.Session()
    
    # Data para cookies
    new_date = datetime.now() - timedelta(days=1)
    
    # Configurar cookies para sessão que são necessários para acessar o site
    cookies = {
        'cookieConsent': 'true',
        'cookieCompliance': 'accepted',
        'tc_visitors': '7f13456a-0a79-459b-9bb5-fe98f89542c0',
        'device_view': 'full',
        'OptanonAlertBoxClosed': new_date.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        'locale': 'es',
        '_gcl_au': '1.1.123456789.1234567890',
        '_ga': 'GA1.1.123456789.1234567890',
        '_ga_JNFZGVL6HL': 'GS1.1.1234567890.1.1.1234567890.0.0.0',
    }
    
    # Aplicar cookies à sessão
    for name, value in cookies.items():
        session.cookies.set(name, value, domain='888casino.com')
        session.cookies.set(name, value, domain='888casino.es')
        session.cookies.set(name, value, domain='www.888casino.es')
    
    # Mapeamento de nomes de roletas por idioma (para normalização)
    mapeamento_nomes = {
        "888 Live Roulette": "888 Ruleta En Vivo",
        "Lightning Roulette": "Ruleta Lightning",
        "Speed Roulette": "Ruleta Speed 888",
        "Mega Fire Blaze Live Roulette": "Mega Fire Blaze Ruleta En Vivo",
        "Grand Roulette": "Grand Ruleta",
        "Roulette": "Ruleta",
        "XXXtreme Lightning Roulette": "XXXtreme Lightning Ruleta",
        "Auto Roulette": "Auto Ruleta",
        "Immersive Roulette": "Ruleta Inmersiva"
    }
    
    cycle_count = 0
    last_success_time = time.time()
    
    while executando:
        try:
            dados_extraidos = False
            cycle_count += 1
            logger.info(f"Ciclo de extração {cycle_count} - Tentando obter APENAS dados REAIS (sem simulação)")
            
            # Pré-aquecer a sessão visitando a página principal (para conseguir cookies legítimos)
            try:
                logger.info("Pré-aquecendo sessão para evitar bloqueios...")
                pre_warm_url = "https://es.888casino.com/"
                session.get(pre_warm_url, headers=headers, timeout=20)
                time.sleep(1)  # Pequena pausa como um navegador real faria
                
                # Visitar página de casino ao vivo para obter mais cookies
                logger.info("Visitando página de casino ao vivo...")
                session.get(url, headers=headers, timeout=20)
                time.sleep(1)
            except Exception as e:
                logger.warning(f"Erro no pré-aquecimento, mas continuando: {str(e)}")
            
            # PASSO 1: Tentar obter dados das APIs diretas primeiro
            for api_url in api_urls:
                try:
                    # Tentar com diferentes métodos HTTP - primeiro GET, depois POST
                    for method in ["GET", "POST"]:
                        logger.info(f"Tentando API direta ({method}): {api_url}")
                        
                        # Adicionar timestamp para evitar cache
                        timestamp = int(time.time() * 1000)
                        url_with_timestamp = f"{api_url}{'&' if '?' in api_url else '?'}_t={timestamp}"
                        
                        if method == "GET":
                            response = session.get(url_with_timestamp, headers=json_headers, timeout=15)
                        else:
                            # Para POST, enviar alguns dados básicos que o site pode esperar
                            payload = {
                                "category": "roulette", 
                                "filter": "live", 
                                "locale": "es-ES",
                                "platform": "desktop",
                                "clientTime": timestamp,
                                "requestId": f"req_{timestamp}"
                            }
                            response = session.post(url_with_timestamp, headers=json_headers, json=payload, timeout=15)
                        
                        # Se recebemos uma resposta, registrar os cookies obtidos
                        if response.cookies:
                            logger.info(f"Cookies recebidos: {[c for c in response.cookies]}")
                            # Aplicar automaticamente à sessão
                        
                        if response.status_code == 200:
                            try:
                                # Tentar interpretar como JSON
                                data = response.json()
                                logger.info(f"Resposta da API obtida ({method}): {api_url}")
                                
                                # Procurar por dados de roleta na resposta
                                roletas_encontradas = 0
                                
                                # Imprimir estrutura da resposta para análise (apenas em debug)
                                logger.debug(f"Estrutura da resposta: {list(data.keys()) if isinstance(data, dict) else 'Lista'}")
                                
                                # Verificar diferentes estruturas de resposta
                                if isinstance(data, dict):
                                    # Tentar padrão: {"games": [...]}
                                    if "games" in data and isinstance(data["games"], list):
                                        for game in data["games"]:
                                            if (("type" in game and "roulette" in game.get("type", "").lower()) or
                                                ("gameType" in game and "roulette" in game.get("gameType", "").lower()) or
                                                ("category" in game and "roulette" in game.get("category", "").lower()) or
                                                ("name" in game and "ruleta" in game.get("name", "").lower()) or
                                                ("name" in game and "roulette" in game.get("name", "").lower())):
                                                
                                                nome_roleta = game.get("name", "")
                                                # Normalizar nome se possível
                                                if nome_roleta in mapeamento_nomes:
                                                    nome_roleta = mapeamento_nomes[nome_roleta]
                                                    
                                                # Verificar diferentes campos para histórico
                                                numeros_historico = []
                                                for history_field in ["history", "lastResults", "results", "numbers", "recentNumbers", "pastResults"]:
                                                    if history_field in game and isinstance(game[history_field], list):
                                                        for n in game[history_field]:
                                                            # Tenta converter tanto inteiros quanto strings
                                                            try:
                                                                num = int(n) if isinstance(n, (int, str)) else n.get("number", 0) if isinstance(n, dict) else 0
                                                                if 0 <= num <= 36:
                                                                    numeros_historico.append(num)
                                                            except (ValueError, TypeError):
                                                                pass
                                                
                                                if nome_roleta and numeros_historico:
                                                    logger.info(f"API: Encontrada roleta {nome_roleta} com números: {numeros_historico}")
                                                    processar_roleta_com_numeros(nome_roleta, numeros_historico)
                                                    roletas_encontradas += 1
                                                    dados_extraidos = True
                                    
                                    # Verificar outras estruturas possíveis
                                    for possible_key in ["data", "result", "content", "liveGames"]:
                                        if possible_key in data and isinstance(data[possible_key], (dict, list)):
                                            sub_data = data[possible_key]
                                            
                                            # Se é um dicionário, procurar por uma lista de roletas
                                            if isinstance(sub_data, dict):
                                                for list_key in ["roulettes", "games", "roulette", "items"]:
                                                    if list_key in sub_data and isinstance(sub_data[list_key], list):
                                                        for roleta in sub_data[list_key]:
                                                            if not isinstance(roleta, dict):
                            continue
                        
                                                            nome_roleta = roleta.get("name", "")
                                                            if nome_roleta in mapeamento_nomes:
                                                                nome_roleta = mapeamento_nomes[nome_roleta]
                                                                
                                                            # Verificar diferentes campos para histórico
                                                            numeros_historico = []
                                                            for history_field in ["numbers", "history", "results", "recentNumbers"]:
                                                                if history_field in roleta and isinstance(roleta[history_field], list):
                                                                    for n in roleta[history_field]:
                                                                        try:
                                                                            num = int(n) if isinstance(n, (int, str)) else n.get("number", 0) if isinstance(n, dict) else 0
                                                                            if 0 <= num <= 36:
                                                                                numeros_historico.append(num)
                                                                        except (ValueError, TypeError):
                                                                            pass
                                                            
                                                            if nome_roleta and numeros_historico:
                                                                logger.info(f"API: Encontrada roleta {nome_roleta} com números: {numeros_historico}")
                                                                processar_roleta_com_numeros(nome_roleta, numeros_historico)
                                                                roletas_encontradas += 1
                                                                dados_extraidos = True
                                            
                                            # Se é uma lista, processar diretamente
                                            elif isinstance(sub_data, list):
                                                for roleta in sub_data:
                                                    if not isinstance(roleta, dict):
                                                        continue
                                                        
                                                    nome_roleta = roleta.get("name", "")
                                                    if nome_roleta in mapeamento_nomes:
                                                        nome_roleta = mapeamento_nomes[nome_roleta]
                                                        
                                                    # Verificar diferentes campos para histórico
                                                    numeros_historico = []
                                                    for history_field in ["numbers", "history", "results", "recentNumbers"]:
                                                        if history_field in roleta and isinstance(roleta[history_field], list):
                                                            for n in roleta[history_field]:
                                                                try:
                                                                    num = int(n) if isinstance(n, (int, str)) else n.get("number", 0) if isinstance(n, dict) else 0
                                                                    if 0 <= num <= 36:
                                                                        numeros_historico.append(num)
                                                                except (ValueError, TypeError):
                                                                    pass
                                                    
                                                    if nome_roleta and numeros_historico:
                                                        logger.info(f"API: Encontrada roleta {nome_roleta} com números: {numeros_historico}")
                                                        processar_roleta_com_numeros(nome_roleta, numeros_historico)
                                                        roletas_encontradas += 1
                                                        dados_extraidos = True
                                
                                # Verificar se é uma lista direta de roletas
                                elif isinstance(data, list):
                                    for roleta in data:
                                        if not isinstance(roleta, dict):
                                            continue
                                            
                                        nome_roleta = roleta.get("name", "")
                                        if nome_roleta in mapeamento_nomes:
                                            nome_roleta = mapeamento_nomes[nome_roleta]
                                            
                                        # Verificar diferentes campos para histórico
                                        numeros_historico = []
                                        for history_field in ["numbers", "history", "results", "recentNumbers"]:
                                            if history_field in roleta and isinstance(roleta[history_field], list):
                                                for n in roleta[history_field]:
                                                    try:
                                                        num = int(n) if isinstance(n, (int, str)) else n.get("number", 0) if isinstance(n, dict) else 0
                                                        if 0 <= num <= 36:
                                                            numeros_historico.append(num)
                                                    except (ValueError, TypeError):
                                                        pass
                                        
                                        if nome_roleta and numeros_historico:
                                            logger.info(f"API: Encontrada roleta {nome_roleta} com números: {numeros_historico}")
                                            processar_roleta_com_numeros(nome_roleta, numeros_historico)
                                            roletas_encontradas += 1
                                            dados_extraidos = True
                                
                                if roletas_encontradas > 0:
                                    logger.info(f"Total de {roletas_encontradas} roletas extraídas com sucesso da API ({method})")
                                    last_success_time = time.time()
                                    break  # Sair do loop de método HTTP
                                    
                            except ValueError:
                                logger.warning(f"Resposta da API não é JSON válido: {api_url}")
                        else:
                            logger.warning(f"API retornou status {response.status_code} ({method}): {api_url}")
                    
                    if dados_extraidos:
                        break  # Sair do loop de API URLs
    
    except Exception as e:
                    logger.error(f"Erro ao acessar API {api_url}: {str(e)}")
            
            # PASSO 2: Se não conseguimos dados das APIs, tentar webscraping direto
            if not dados_extraidos:
                logger.info("APIs diretas falharam. Tentando webscraping direto...")
                
                try:
                    logger.info(f"Tentando webscraping de: {url}")
                    
                    # Adicionar um cookie de aceitação de cookies para evitar pop-ups
                    session.cookies.set("cookieConsent", "true", domain="888casino.com")
                    session.cookies.set("cookieCompliance", "accepted", domain="888casino.com")
                    
                    response = session.get(url, headers=headers, timeout=30)
                    
                    if response.status_code == 200:
                        logger.info(f"Página carregada com sucesso: {url}")
                        
                        # Salvar HTML para debug se necessário
                        # with open("888casino_page.html", "w", encoding="utf-8") as f:
                        #    f.write(response.text)
                        
                        # Usar BeautifulSoup para extrair dados
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        # Seletores atualizados para o site atual
                        seletores_roletas = [
                            # Seletores atualizados e expandidos
                            '.game-tile-container', '.lobby-game', '.game-tile', '.roulette-item',
                            '.live-roulette-item', '.casino-game-item', '.live-casino-item',
                            '[data-game-type="roulette"]', '[data-category="roulette"]',
                            '[data-game-id*="roulette"]', '[class*="roulette"]',
                            # Seletores gerais que podem conter jogos
                            '.game-list-item', '.game-container', '.game-wrapper'
                        ]
                        
                        # Tentar todos os seletores possíveis
                        roleta_items = []
                        for seletor in seletores_roletas:
                            items = soup.select(seletor)
                            if items:
                                logger.info(f"Encontrados {len(items)} elementos com seletor '{seletor}'")
                                roleta_items.extend(items)
                        
                        # Remover duplicatas (convertendo para conjunto e de volta para lista)
                        roleta_items = list({item: None for item in roleta_items}.keys())
                        
                        if roleta_items:
                            logger.info(f"Encontrados {len(roleta_items)} elementos de roleta no total")
                            
                            for item in roleta_items:
                                try:
                                    # Depuração
                                    # logger.debug(f"HTML do elemento: {item}")
                                    
                                    # Seletores expandidos para título
                                    titulo_seletores = [
                                        '.game-name', '.game-title', '.title', 'h3', 'h4', 
                                        '[class*="title"]', '[class*="name"]', '.game-info-name',
                                        'span[data-game-name]', '[data-title]'
                                    ]
                                    
                                    # Tentar todos os seletores para título
                                    titulo_element = None
                                    for selector in titulo_seletores:
                                        titulo_element = item.select_one(selector)
                                        if titulo_element:
                                    break
                        
                                    # Se ainda não encontrou, procurar atributos
                                    if not titulo_element:
                                        for attr in ['data-game-name', 'data-name', 'data-title', 'title', 'alt']:
                                            if item.has_attr(attr):
                                                titulo = item[attr].strip()
                                                break
                                    else:
                                        titulo = titulo_element.text.strip()
                                    
                                    if not titulo:
                                        # Tentar encontrar em elementos aninhados
                                        img_with_alt = item.select_one('img[alt]')
                                        if img_with_alt and img_with_alt.get('alt'):
                                            titulo = img_with_alt.get('alt')
                                    
                                    if not titulo:
                        continue
                    
                                    # Filtrar para garantir que é uma roleta
                                    if not ('ruleta' in titulo.lower() or 'roulette' in titulo.lower()):
                                        continue
                                    
                                    # Seletores expandidos para números
                                    numero_seletores = [
                                        '.result', '.number', '.history', '.past-results', '.recent-numbers',
                                        '[class*="result"]', '[class*="number"]', '[class*="history"]',
                                        '.results-container span', '.numbers-container span', 
                                        '[data-results]', '[data-history]'
                                    ]
                                    
                                    numeros_atuais = []
                                    
                                    # Tentar vários métodos para obter números
                                    for selector in numero_seletores:
                                        elementos = item.select(selector)
                                        if elementos:
                                            for elem in elementos:
                                                num_text = elem.text.strip()
                                                if num_text.isdigit() and 0 <= int(num_text) <= 36:
                                                    numeros_atuais.append(int(num_text))
                                    
                                    # Tentar atributos data
                                    if not numeros_atuais:
                                        for attr in ['data-results', 'data-history', 'data-numbers']:
                                            if item.has_attr(attr):
                                                try:
                                                    attr_value = item[attr]
                                                    # Tentar interpretar como JSON
                                                    try:
                                                        numbers_data = json.loads(attr_value)
                                                        if isinstance(numbers_data, list):
                                                            for n in numbers_data:
                                                                if isinstance(n, int) and 0 <= n <= 36:
                                                                    numeros_atuais.append(n)
                                                                elif isinstance(n, str) and n.isdigit() and 0 <= int(n) <= 36:
                                                                    numeros_atuais.append(int(n))
                                                    except json.JSONDecodeError:
                                                        # Se não for JSON, tentar extrair números diretamente
                                                        numeros_atuais = [int(n) for n in re.findall(r'\d+', attr_value) 
                                                                          if n.isdigit() and 0 <= int(n) <= 36]
                                                except:
                                                    pass
                                    
                                    # Se ainda não tem números, procurar em todo o texto
                                    if not numeros_atuais:
                                        # Procurar em qualquer texto contido no elemento
                                        all_text = item.get_text()
                                        # Tentar encontrar sequências de números
                                        matches = re.findall(r'\b(\d{1,2})\b', all_text)
                                        numeros_atuais = [int(n) for n in matches if n.isdigit() and 0 <= int(n) <= 36]
                                    
                                    if numeros_atuais:
                                        logger.info(f"Extraídos números para {titulo}: {numeros_atuais}")
                                        processar_roleta_com_numeros(titulo, numeros_atuais)
                                        dados_extraidos = True
                                        last_success_time = time.time()
                                except Exception as e:
                                    logger.error(f"Erro ao processar elemento de roleta: {str(e)}")
                        else:
                            # Tenta extração mais agressiva de scripts no HTML
                            logger.warning(f"Nenhum elemento de roleta encontrado com seletores normais. Tentando extrair de scripts...")
                            
                            # Procurar por dados em scripts JSON ou variáveis JavaScript
                            scripts = soup.find_all('script')
                            for script in scripts:
                                script_text = script.string
                                if not script_text:
                        continue
                    
                                # Procurar por JSON ou objetos JavaScript com dados de roleta
                                for keyword in ['roulette', 'ruleta', 'gameData', 'liveGames', 'casinoGames']:
                                    if keyword in script_text:
                                        # Tentar extrair JSON
                                        json_matches = re.findall(r'(\{.*?".*?".*?\})', script_text)
                                        for json_str in json_matches:
                                            try:
                                                # Adicionar chaves para tentar formar um JSON válido
                                                data = json.loads(json_str)
                                                if isinstance(data, dict):
                                                    # Procurar dados de roleta
                                                    if 'name' in data and ('roulette' in data['name'].lower() or 'ruleta' in data['name'].lower()):
                                                        nome = data.get('name', '')
                    numeros = []
                                                        
                                                        # Procurar números em vários campos possíveis
                                                        for field in ['numbers', 'history', 'results', 'recentNumbers']:
                                                            if field in data and isinstance(data[field], list):
                                                                for n in data[field]:
                                                                    try:
                                                                        num = int(n) if isinstance(n, (int, str)) else (
                                                                            n.get("number", 0) if isinstance(n, dict) else 0
                                                                        )
                                                                        if 0 <= num <= 36:
                                                                            numeros.append(num)
                                                                    except (ValueError, TypeError):
                                                                        pass
                                                        
                                                        if nome and numeros:
                                                            logger.info(f"Extraídos dados de script para {nome}: {numeros}")
                                                            processar_roleta_com_numeros(nome, numeros)
                                                            dados_extraidos = True
                                                            last_success_time = time.time()
                                            except json.JSONDecodeError:
                                                pass
                            
                            if not dados_extraidos:
                                logger.warning(f"Nenhum elemento de roleta encontrado na página: {url}")
        else:
                        logger.warning(f"Falha ao carregar página {url}: Status {response.status_code}")
                except Exception as e:
                    logger.error(f"Erro durante webscraping de {url}: {str(e)}")
            
            # Se não conseguimos dados novos, buscar dados existentes do Supabase
            # (isso não é simulação, apenas busca dados reais anteriores)
            if not dados_extraidos:
                logger.info("Tentando obter dados existentes do Supabase...")
                
                try:
                    result = supabase.table("roletas").select("*").execute()
                    
                    if result.data and len(result.data) > 0:
                        logger.info(f"Obtidos {len(result.data)} registros existentes do Supabase")
                        
                        for roleta in result.data:
                            nome_roleta = roleta.get("nome", "")
                            numeros = roleta.get("numeros", [])
                            
                            if nome_roleta and numeros and len(numeros) > 0:
                                logger.info(f"Usando dados existentes para {nome_roleta}: {numeros[:5]}...")
                                
                                # Não estamos gerando novos números, apenas usando os que já existem
                                if nome_roleta not in numeros_roletas:
                                    numeros_roletas[nome_roleta] = {
                                            "numeros": numeros,
                                        "ultima_atualizacao": roleta.get("updated_at", datetime.now().isoformat()),
                                        "estrategia": {},
                                        "id": roleta.get("id", f"roleta-{hash(nome_roleta) % 100000}")
                                    }
                                    
                                    # Inicializar analisador de estratégia com os números existentes
                                    if nome_roleta not in analisadores_mesas:
                                        analisadores_mesas[nome_roleta] = StrategyAnalyzer()
                                        
                                        # Processar todos os números existentes para reconstruir o estado
                                        # do analisador (sem gerar novos números)
                                        for num in numeros:
                                            analisadores_mesas[nome_roleta].process_number(num)
                                    
                                    # Atualizar estratégia
                                    numeros_roletas[nome_roleta]["estrategia"] = analisadores_mesas[nome_roleta].get_status()
                                    dados_extraidos = True
                                    
                        if dados_extraidos:
                            logger.info("Usando dados existentes do Supabase até conseguir extrair novos dados reais")
                    else:
                        logger.warning("Nenhum dado encontrado no Supabase")
    except Exception as e:
                    logger.error(f"Erro ao obter dados do Supabase: {str(e)}")
            
            # Se conseguimos extrair dados reais, atualizar o Supabase
            if dados_extraidos:
                current_time = time.time()
                if current_time - last_update_time > 30:  # Atualizar a cada 30 segundos
                    atualizar_supabase(numeros_roletas)
                    last_update_time = current_time
                    logger.info("Dados atualizados no Supabase")
            else:
                # Se estamos há muito tempo sem conseguir dados, registrar um alerta
                current_time = time.time()
                minutes_since_last_success = (current_time - last_success_time) / 60
                if minutes_since_last_success > 5:  # Alerta após 5 minutos sem dados
                    logger.error(f"ALERTA: Não foi possível obter dados reais por {int(minutes_since_last_success)} minutos")
                    logger.error("Por favor, verifique sua conexão ou se o site mudou seu layout/API")
            
            # Esperar antes da próxima tentativa
            tempo_espera = 5  # Aguardar 5 segundos entre ciclos
            logger.info(f"Ciclo {cycle_count} completo. Próximo ciclo em {tempo_espera} segundos.")
            time.sleep(tempo_espera)
            
        except Exception as e:
            logger.error(f"Erro geral na extração: {str(e)}")
            time.sleep(10)  # Aguardar 10 segundos em caso de erro geral

def processar_roleta_com_numeros(nome_roleta, numeros):
    """Função auxiliar para processar uma roleta com números obtidos"""
    global numeros_roletas, analisadores_mesas
    
    if not nome_roleta or not numeros or len(numeros) == 0:
        return False
        
        # Criar analisador para mesa se não existir
        if nome_roleta not in analisadores_mesas:
        analisadores_mesas[nome_roleta] = StrategyAnalyzer()
            logger.info(f"Novo analisador criado para mesa: {nome_roleta}")
        
    # Obter último número
    ultimo_numero = numeros[0]
    
    # Inicializar estrutura de dados se necessário
    if nome_roleta not in numeros_roletas:
        numeros_roletas[nome_roleta] = {
            "numeros": [],
            "ultima_atualizacao": "",
            "estrategia": {},
            "id": f"roleta-{hash(nome_roleta) % 100000}"
        }
    
    # Verificar se é um número novo
    numeros_anteriores = numeros_roletas.get(nome_roleta, {}).get("numeros", [])
    if not numeros_anteriores or ultimo_numero != numeros_anteriores[0]:
        # Processar número no analisador
        analisadores_mesas[nome_roleta].process_number(ultimo_numero)
        
        # Atualizar números - adicionar apenas os que não existem
        numeros_existentes = set(numeros_roletas[nome_roleta]["numeros"])
        novos_numeros = [n for n in numeros if n not in numeros_existentes]
        numeros_roletas[nome_roleta]["numeros"] = novos_numeros + numeros_roletas[nome_roleta]["numeros"]
        
        # Limitar o tamanho da lista
        numeros_roletas[nome_roleta]["numeros"] = numeros_roletas[nome_roleta]["numeros"][:20]
        
        # Atualizar timestamp e estratégia
        timestamp_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        numeros_roletas[nome_roleta].update({
            "ultima_atualizacao": timestamp_atual,
            "estrategia": analisadores_mesas[nome_roleta].get_status()
        })
        
        logger.info(f"Número processado para {nome_roleta}: {ultimo_numero}")
        return True
    
    return False

def extrair_numeros():
    global driver, executando, numeros_roletas, analisadores_mesas
    
    if IS_RAILWAY:
        logger.warning("Extração via Selenium não disponível no Railway. Use o método API.")
        return
    
    # Contador para limitar redirecionamentos
    redirection_count = 0
    last_redirection_time = time.time()
    
    while executando:
        try:
            # Verificar URL atual e redirecionar se necessário, mas com limitação
            current_url = driver.current_url
            current_time = time.time()
            
            if ("888casino.com" not in current_url or "live-casino" not in current_url) and \
               (current_time - last_redirection_time > 60 or redirection_count < 3):
                logging.warning("URL incorreta detectada, redirecionando...")
                driver.get("https://es.888casino.com/live-casino/#filters=live-roulette")
                time.sleep(5)
                redirection_count += 1
                last_redirection_time = current_time
            elif current_time - last_redirection_time > 300:
                # Reset counter every 5 minutes
                redirection_count = 0
            
            # Encontrar todas as roletas
            elementos = WebDriverWait(driver, 15).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "cy-live-casino-grid-item"))
            )
            
            # Log the number of roulette elements found
            logging.info(f"Encontradas {len(elementos)} roletas na página")
            
            # Process all roulette tables instead of filtering
            for elemento in elementos:
                try:
                    # Extrair título da roleta
                    titulo = elemento.find_element(By.CLASS_NAME, "cy-live-casino-grid-item-title").text
                    
                    # Log the roulette title for debugging
                    logging.info(f"Processando roleta: {titulo}")
                    
            # Criar analisador para mesa se não existir
                    if titulo not in analisadores_mesas:
                        analisadores_mesas[titulo] = StrategyAnalyzer()
                        logging.info(f"Novo analisador criado para mesa: {titulo}")
                    
                    # Extrair todos os números usando JavaScript - método mais robusto
                    numeros_atuais = driver.execute_script("""
                        function extrairNumeros(elemento) {
                            try {
                                let numeros = [];
                                
                                // Primeiro método: buscar spans com números
                                let spans = elemento.querySelectorAll('.cy-live-casino-grid-item-infobar-draws span, .cy-live-casino-grid-item-infobar-draws div');
                                if (spans && spans.length > 0) {
                                    numeros = Array.from(spans)
                                        .filter(span => span && span.textContent)
                                        .map(span => span.textContent.trim())
                                        .filter(texto => /^\\d+$/.test(texto))
                                        .map(num => parseInt(num));
                                }
                                
                                // Segundo método: buscar no texto completo da div de números
                                if (numeros.length === 0) {
                                    let infobar = elemento.querySelector('.cy-live-casino-grid-item-infobar-draws');
                                    if (infobar && infobar.textContent) {
                                        let matches = infobar.textContent.match(/\\d+/g);
                                        if (matches) {
                                            numeros = matches.map(num => parseInt(num));
                                        }
                                    }
                                }
                                
                                // Terceiro método: tentar outros seletores comuns
                                if (numeros.length === 0) {
                                    let possiveisSeletores = [
                                        '.number', '.roulette-number', '.result', 
                                        '[data-result]', '[data-number]',
                                        '[data-latest-result]', '.latest-result',
                                        '.previous-results', '.history-numbers',
                                        '.game-history', '.recent-numbers',
                                        '.roulette-results', '.game-results'
                                    ];
                                    
                                    for (let seletor of possiveisSeletores) {
                                        let elementos = elemento.querySelectorAll(seletor);
                                        if (elementos && elementos.length > 0) {
                                            let novosNumeros = Array.from(elementos)
                                                .filter(el => el && el.textContent)
                                                .map(el => el.textContent.trim())
                                                .filter(texto => /^\\d+$/.test(texto))
                                                .map(num => parseInt(num));
                                            
                                            if (novosNumeros.length > 0) {
                                                numeros = numeros.concat(novosNumeros);
                                            }
                                        }
                                    }
                                }
                                
                                // Quarto método: tentar atributos data-*
                                let dataElements = elemento.querySelectorAll('[data-latest-result], [data-number], [data-value]');
                                if (dataElements && dataElements.length > 0) {
                                    dataElements.forEach(el => {
                                        ['data-latest-result', 'data-number', 'data-value'].forEach(attr => {
                                            if (el.hasAttribute(attr)) {
                                                let valor = el.getAttribute(attr);
                                                if (valor && /^\\d+$/.test(valor)) {
                                                    numeros.push(parseInt(valor));
                                                }
                                            }
                                        });
                                    });
                                }
                                
                                // Remover duplicatas e retornar
                                return [...new Set(numeros)];
                            } catch (error) {
                                console.error('Erro ao extrair números:', error);
                                return [];
                            }
                        }
                        return extrairNumeros(arguments[0]);
                    """, elemento)
                    
                    # Log the extracted numbers for debugging
                    logging.info(f"Números extraídos para {titulo}: {numeros_atuais}")
                    
                    if numeros_atuais and len(numeros_atuais) > 0:
                        ultimo_numero = numeros_atuais[0]  # O primeiro número é o mais recente
                        
                        # Verificar se é um número novo comparando com o histórico atual
                        numeros_anteriores = numeros_roletas.get(titulo, {}).get("numeros", [])
                        if not numeros_anteriores or ultimo_numero != numeros_anteriores[0]:
                            logging.info(f"Novo número detectado para {titulo}: {ultimo_numero}")
                            
                            # Processar número na estratégia específica da mesa
                            analisadores_mesas[titulo].process_number(ultimo_numero)
                            
                            # Manter histórico acumulado de números, limitando o tamanho
                            if titulo not in numeros_roletas:
                                numeros_roletas[titulo] = {
                                    "numeros": [],
                                    "ultima_atualizacao": "",
                                    "estrategia": {},
                                    "id": f"roleta-{hash(titulo) % 100000}"
                                }
                            
                            # Adicionar novos números ao início da lista, evitando duplicatas e limitando tamanho
                            numeros_existentes = set(numeros_roletas[titulo]["numeros"])
                            novos_numeros = [n for n in numeros_atuais if n not in numeros_existentes]
                            numeros_roletas[titulo]["numeros"] = (novos_numeros + numeros_roletas[titulo]["numeros"])[:20]  # Limitar a 20 números
                            
                            # Atualizar timestamp e status da estratégia
                            timestamp_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            numeros_roletas[titulo].update({
                                "ultima_atualizacao": timestamp_atual,
                                "estrategia": analisadores_mesas[titulo].get_status()
                            })
                            
                            # Enviar dados para o Supabase
                            atualizar_supabase({titulo: numeros_roletas[titulo]})
                            logging.info(f"Números atualizados para {titulo}: {numeros_roletas[titulo]['numeros']}")
        else
                        logging.warning(f"Nenhum número encontrado para a mesa {titulo} - aguardando próxima atualização")
    except Exception as e:
                    logging.error(f"Erro ao processar roleta {titulo if 'titulo' in locals() else 'desconhecida'}: {str(e)}")
            
            # Delay fixo entre verificações (sem aleatoriedade para evitar simulação)
            time.sleep(2.5)  # Valor fixo em vez de random.uniform
                    
        except Exception as e:
            logging.error(f"Erro na extração: {str(e)}")
            
            # Se houver erro, tentar reiniciar o driver, mas com menos frequência
            try:
                if driver:
                    driver.quit()
                driver = configurar_driver()
                navegar_para_site(driver)
                # Reset contador de redirecionamentos após reiniciar o driver
                redirection_count = 0
                last_redirection_time = time.time()
            except Exception as e:
                logging.error(f"Erro ao reiniciar driver: {str(e)}")
                time.sleep(30)  # Esperar mais tempo antes de tentar novamente

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/iniciar')
def iniciar():
    global driver, thread_extracao, executando
    
    if not executando:
        try:
            executando = True
            
            if IS_RAILWAY:
                # No Railway, usar método API
                logger.info("Iniciando extração via API (modo Railway)")
                thread_extracao = threading.Thread(target=extrair_dados_api)
            else:
                # Em ambiente local, usar Selenium
                driver = configurar_driver()
                if driver:
                    navegar_para_site(driver)
                    thread_extracao = threading.Thread(target=extrair_numeros)
                else:
                    # Fallback para API se o driver falhar
                    logger.warning("Driver falhou, caindo para método API")
                    thread_extracao = threading.Thread(target=extrair_dados_api)
            
            thread_extracao.daemon = True
            thread_extracao.start()
            
            return jsonify({"status": "success", "message": "Extração iniciada"})
        except Exception as e:
            executando = False
            logging.error(f"Erro ao iniciar: {str(e)}")
            return jsonify({"status": "error", "message": f"Erro ao iniciar: {str(e)}"})
    else:
        return jsonify({"status": "warning", "message": "Extração já está em execução"})

@app.route('/parar')
def parar():
    global driver, executando
    
    if executando:
        executando = False
        if driver:
            driver.quit()
            driver = None
        return jsonify({"status": "success", "message": "Extração parada"})
    else:
        return jsonify({"status": "warning", "message": "Extração não está em execução"})

@app.route('/dados')
def dados():
    """Retorna os dados da extração."""
    try:
        # Obter dados do Supabase
        result = supabase.table("roletas").select("*").execute()
        dados_roletas = {}
        
        if result.data:
            for roleta in result.data:
                dados_roletas[roleta["nome"]] = roleta
        
        return jsonify(dados_roletas)
        except Exception as e:
        app.logger.error(f"Erro ao obter dados do Supabase: {str(e)}")
        return jsonify({
            'error': f"Falha ao conectar com Supabase: {str(e)}"
        }), 500

@app.route('/sync_supabase')
def sync_supabase():
    """Endpoint para sincronizar dados manualmente com o Supabase"""
    if numeros_roletas:
        try:
            result = atualizar_supabase(numeros_roletas)
            if result:
                return jsonify({"status": "success", "message": "Dados sincronizados com o Supabase"})
            else:
                return jsonify({"status": "error", "message": "Falha ao sincronizar dados"})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Erro ao sincronizar: {str(e)}"})
    else:
        return jsonify({"status": "warning", "message": "Nenhum dado para sincronizar"})

def scrape_roletas():
    """Função principal que inicia o scraper"""
    logger.info("Iniciando scraper em modo contínuo")
    logger.info("Iniciando scraper sem modo simulado")
    logger.info("Modo de dados simulados DESATIVADO - usando extração real")
    
    global executando
    executando = True
    
    try:
        if IS_RAILWAY:
            # No Railway, usar método API
            logger.info("Detectado ambiente Railway - usando extração via API")
            extrair_dados_api()
        else:
            # Em ambiente local, tentar usar Selenium
            driver = configurar_driver()
            if driver:
                navegar_para_site(driver)
                extrair_numeros()
            else:
                # Fallback para API se o driver falhar
                logger.warning("Driver falhou, caindo para método API")
                extrair_dados_api()
    except Exception as e:
        logger.error(f"Erro ao iniciar scraper: {str(e)}")
        if 'driver' in locals() and driver:
            driver.quit()
        executando = False

if __name__ == '__main__':
    # Iniciar o scraper em um thread separado
    thread_scraper = threading.Thread(target=scrape_roletas)
    thread_scraper.daemon = True
    thread_scraper.start()
    
    # Obter porta do Heroku ou usar 5000 como padrão
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
