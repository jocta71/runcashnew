import time
import random
import re
import json
import os
import platform
from datetime import datetime
import logging
import requests
from bs4 import BeautifulSoup
from supabase import create_client
from flask import Flask, render_template, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import threading
from strategy_analyzer import StrategyAnalyzer
from enum import Enum
from terminal_table import TERMINAL_TABLE

from config import CASINO_URL, SUPABASE_URL, SUPABASE_KEY, roleta_permitida_por_id, logger, MAX_CICLOS

# Detectar se estamos no Railway
IS_RAILWAY = "RAILWAY_STATIC_URL" in os.environ or "RAILWAY_SERVICE_ID" in os.environ

# Inicialização do cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Dicionário global para manter os analisadores de cada mesa
analisadores_mesas = {}

# Intervalo de verificação em segundos
VERIFICACAO_INTERVALO = 3

# URLs possíveis para acessar - tanto a original quanto a redirecionada
CASINO_URLS = [
    "https://es.888casino.com/live-casino/#filters=live-roulette",  # URL original
    "https://www.888casino.es/ruleta-en-vivo/#filters=live-roulette"  # URL redirecionada
]

# Limite de falhas consecutivas antes de usar dados simulados
MAX_FALHAS_PERMITIDAS = 3

# Flag para controlar modo de extração
USAR_DADOS_SIMULADOS = False

app = Flask(__name__)

# Variáveis globais para armazenar dados
numeros_roletas = {}
driver = None
thread_extracao = None
executando = False

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

def get_random_user_agent():
    """Retorna um user agent aleatório para reduzir a chance de detecção"""
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15'
    ]
    return random.choice(user_agents)

def configurar_driver(tentativa=1, max_tentativas=3):
    print("Configurando driver para Heroku...")
    
    try:
        # Configurações específicas para o Heroku
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"user-agent={get_random_user_agent()}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Verificar ambiente - Heroku vs Local
        is_heroku = os.environ.get('DYNO') is not None
        
        if is_heroku:
            # Imprimir variáveis de ambiente para debug
            logging.info(f"PATH: {os.environ.get('PATH', 'Não definido')}")
            logging.info(f"CHROME_BIN: {os.environ.get('CHROME_BIN', 'Não definido')}")
            logging.info(f"CHROMEDRIVER_PATH: {os.environ.get('CHROMEDRIVER_PATH', 'Não definido')}")
            
            # Tentar usar o Chrome sem especificar o binário ou o chromedriver
            try:
                # No Heroku, vamos tentar usar o Chrome diretamente sem especificar o chromedriver
                # Isso permite que o Selenium encontre o chromedriver automaticamente
                driver = webdriver.Chrome(options=chrome_options)
                logging.info("Driver configurado com sucesso usando Chrome automático")
                return driver
            except Exception as chrome_error:
                logging.error(f"Erro ao inicializar Chrome automático: {str(chrome_error)}")
                
                # Tentar usar o webdriver_manager como fallback
                try:
                    logging.info("Tentando usar webdriver_manager como fallback")
                    from webdriver_manager.chrome import ChromeDriverManager
                    
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    logging.info("Driver configurado com sucesso usando webdriver_manager")
                    return driver
                except Exception as wdm_error:
                    logging.error(f"Erro ao usar webdriver_manager: {str(wdm_error)}")
                    raise
        else:
            # Configuração para ambiente local
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        
        logging.info(f"Driver configurado com sucesso para ambiente {'Heroku' if is_heroku else 'local'}!")
        return driver
        
    except Exception as e:
        logging.error(f"Erro ao configurar driver (tentativa {tentativa}): {str(e)}")
        if tentativa < max_tentativas:
            time.sleep(10)
            return configurar_driver(tentativa + 1, max_tentativas)
        else:
            raise Exception(f"Falha ao configurar driver após {max_tentativas} tentativas")

def navegar_para_site(driver, tentativa=1, max_tentativas=3):
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
        
        # Tentar acessar o site com diferentes URLs - priorizando a versão espanhola
        urls = [
            "https://es.888casino.com/live-casino/#filters=live-roulette",
            "https://www.888casino.es/live-casino/#filters=live-roulette",
            "https://www.888casino.com/live-casino/#filters=live-roulette",
            "https://www.888casino.pt/live-casino/#filters=live-roulette"
        ]
        
        for url in urls:
            try:
                driver.get(url)
                # Aguardar carregamento inicial com timeout maior
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(5)
                
                if "888casino" in driver.current_url and "live-casino" in driver.current_url:
                    logging.info(f"Sucesso ao acessar: {url}")
                    return True
            except Exception as e:
                logging.warning(f"Falha ao acessar {url}: {str(e)}")
                continue
        
        raise Exception("Não foi possível acessar nenhuma URL disponível")
        
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

def extrair_numeros():
    global driver, executando, numeros_roletas, analisadores_mesas
    
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
                    else:
                        logging.warning(f"Nenhum número encontrado para a mesa {titulo} - aguardando próxima atualização")
                            
                except Exception as e:
                    logging.error(f"Erro ao processar roleta {titulo if 'titulo' in locals() else 'desconhecida'}: {str(e)}")
            
            # Delay aleatório entre verificações
            time.sleep(random.uniform(2.0, 3.0))  # Aumentado para reduzir uso de CPU
                    
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
            driver = configurar_driver()
            navegar_para_site(driver)
            
            executando = True
            thread_extracao = threading.Thread(target=extrair_numeros)
            thread_extracao.daemon = True
            thread_extracao.start()
            
            return jsonify({"status": "success", "message": "Extração iniciada"})
        except Exception as e:
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
        driver = configurar_driver()
        navegar_para_site(driver)
        extrair_numeros()
    except Exception as e:
        logger.error(f"Erro ao iniciar scraper: {str(e)}")
        if driver:
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
