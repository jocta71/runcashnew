from flask import Flask, render_template, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import json
import threading
import time
from datetime import datetime
import random
import logging
import sys
import os
from strategy_analyzer import StrategyAnalyzer
from enum import Enum
from terminal_table import TERMINAL_TABLE
from config import ROLETAS_PERMITIDAS  # Importando a lista de roletas permitidas
from firebase_client import FirebaseClient
import base64  # Add this import at the top with other imports
import gc
# Remove psutil import

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
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

# Inicializar cliente Firebase
firebase_client = None
try:
    # Definir função find_credentials_file localmente se não estiver disponível
    # In the find_credentials_file function, update the Base64 handling:
    def find_credentials_file():
        """
        Find the Firebase credentials file in the current directory or environment variables.
        Returns the path to the credentials file or None if not found.
        """
        # Check for Base64-encoded credentials in environment variables first
        firebase_creds_base64 = os.environ.get('FIREBASE_CREDENTIALS_JSON_BASE64')
        if firebase_creds_base64:
            logging.info("Usando credenciais do Firebase codificadas em Base64 da variável de ambiente")
            logging.info(f"Tamanho da string Base64: {len(firebase_creds_base64)}")
            
            # Decode Base64 and save to temporary file
            temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_firebase_creds.json')
            try:
                # Ensure we're working with a clean Base64 string
                # Remove any whitespace that might have been added
                firebase_creds_base64 = firebase_creds_base64.strip()
                
                # Handle URL-safe Base64 encoding (replace - with + and _ with /)
                firebase_creds_base64 = firebase_creds_base64.replace('-', '+').replace('_', '/')
                
                # Add padding if needed
                padding = len(firebase_creds_base64) % 4
                if padding:
                    firebase_creds_base64 += '=' * (4 - padding)
                    
                # Try different decoding approaches
                try:
                    decoded_creds = base64.b64decode(firebase_creds_base64).decode('utf-8')
                except Exception:
                    try:
                        # Try URL-safe decoding
                        decoded_creds = base64.urlsafe_b64decode(firebase_creds_base64).decode('utf-8')
                    except Exception as e:
                        logging.error(f"Falha em ambos os métodos de decodificação: {str(e)}")
                        raise
                
                logging.info(f"Credenciais decodificadas com sucesso, tamanho: {len(decoded_creds)}")
                
                # Validate JSON before writing
                try:
                    json.loads(decoded_creds)
                    logging.info("JSON válido verificado")
                except json.JSONDecodeError as json_err:
                    logging.error(f"JSON inválido após decodificação: {str(json_err)}")
                    logging.error(f"Primeiros 100 caracteres do JSON decodificado: {decoded_creds[:100]}")
                    raise
                    
                with open(temp_file, 'w') as f:
                    f.write(decoded_creds)
                logging.info(f"Credenciais temporárias salvas em: {temp_file}")
                return temp_file
            except Exception as e:
                logging.error(f"Erro ao decodificar credenciais Base64: {str(e)}")
                logging.error(f"Primeiros 20 caracteres da string Base64: {firebase_creds_base64[:20]}...")
        
        # Check for credentials in environment variables first (new method)
        firebase_creds_json = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        if firebase_creds_json:
            logging.info("Usando credenciais do Firebase da variável de ambiente FIREBASE_CREDENTIALS_JSON")
            # Save the JSON content to a temporary file
            temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_firebase_creds.json')
            try:
                with open(temp_file, 'w') as f:
                    f.write(firebase_creds_json)
                logging.info(f"Credenciais temporárias salvas em: {temp_file}")
                return temp_file
            except Exception as e:
                logging.error(f"Erro ao salvar credenciais temporárias: {str(e)}")
        
        # Check environment variable for file path
        creds_file = os.environ.get('FIREBASE_CREDS_FILE')
        if creds_file:
            logging.info(f"Usando arquivo de credenciais da variável de ambiente: {creds_file}")
            return creds_file
        
        # Look for JSON files in the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        for file in os.listdir(current_dir):
            if file.endswith('.json') and 'firebase' in file.lower():
                logging.info(f"Usando arquivo de credenciais encontrado no diretório: {file}")
                return os.path.join(current_dir, file)
        
        # Check common locations
        common_locations = [
            'extrator-roleta-firebase-adminsdk-fbsvc-6799a0ba4d.json',
            'firebase-credentials.json',
            'firebase-adminsdk.json'
        ]
        
        for location in common_locations:
            if os.path.exists(location):
                logging.info(f"Usando arquivo de credenciais de local comum: {location}")
                return location
        
        logging.error("Arquivo de credenciais do Firebase não encontrado")
        return None
    
    # Tentar importar da config, se falhar usar a função local
    try:
        from config import find_credentials_file
    except ImportError:
        logging.info("Função find_credentials_file não encontrada em config, usando implementação local")
    
    creds_file = find_credentials_file()
    if creds_file:
        firebase_client = FirebaseClient(creds_file)
        logging.info(f"Cliente Firebase inicializado com sucesso usando arquivo: {creds_file}")
    else:
        logging.error("Arquivo de credenciais do Firebase não encontrado")
except Exception as e:
    logging.error(f"Erro ao inicializar Firebase: {str(e)}")

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
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36'
    ]
    return random.choice(user_agents)

def configurar_driver(tentativa=1, max_tentativas=3):
    print("Configurando driver com Chromium...")
    
    try:
        # Import ChromeDriverManager here to ensure it's available
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.core.utils import ChromeType
        
        # Configurações específicas para o Chromium
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
        
        # Verificar se existe um caminho específico para o Chromium
        chromium_path = os.environ.get('CHROMIUM_PATH') or os.environ.get('GOOGLE_CHROME_BIN')
        if chromium_path:
            chrome_options.binary_location = chromium_path
            logging.info(f"Usando binário do Chromium em: {chromium_path}")
        
        if is_heroku:
            # Imprimir variáveis de ambiente para debug
            logging.info(f"PATH: {os.environ.get('PATH', 'Não definido')}")
            logging.info(f"CHROME_BIN: {os.environ.get('CHROME_BIN', 'Não definido')}")
            logging.info(f"CHROMEDRIVER_PATH: {os.environ.get('CHROMEDRIVER_PATH', 'Não definido')}")
            
            # Tentar usar o Chromium diretamente
            try:
                chromedriver_path = os.environ.get('CHROMEDRIVER_PATH')
                if chromedriver_path:
                    service = Service(executable_path=chromedriver_path)
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                else:
                    driver = webdriver.Chrome(options=chrome_options)
                logging.info("Driver configurado com sucesso usando Chromium automático")
                return driver
            except Exception as chrome_error:
                logging.error(f"Erro ao inicializar Chromium automático: {str(chrome_error)}")
                
                # Tentar usar o webdriver_manager como fallback com Chromium
                try:
                    logging.info("Tentando usar webdriver_manager com Chromium como fallback")
                    service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    logging.info("Driver configurado com sucesso usando webdriver_manager com Chromium")
                    return driver
                except Exception as chromium_error:
                    logging.error(f"Erro ao usar Chromium com webdriver_manager: {str(chromium_error)}")
                    
                    # Tentar com Chrome normal como último recurso
                    try:
                        logging.info("Tentando usar Chrome normal como último recurso")
                        service = Service(ChromeDriverManager().install())
                        driver = webdriver.Chrome(service=service, options=chrome_options)
                        logging.info("Driver configurado com sucesso usando Chrome normal")
                        return driver
                    except Exception as wdm_error:
                        logging.error(f"Erro ao usar webdriver_manager com Chrome: {str(wdm_error)}")
                        raise
        else:
            # Configuração para ambiente local com Chromium
            try:
                service = Service(ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                logging.info("Driver configurado com sucesso usando Chromium local")
            except Exception as chromium_error:
                logging.error(f"Erro ao configurar Chromium local: {str(chromium_error)}")
                logging.info("Tentando com Chrome normal")
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=chrome_options)
                logging.info("Driver configurado com sucesso usando Chrome local")
        
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
        driver.set_page_load_timeout(120)  # Aumentado para 120 segundos
        
        # Limpar cookies e cache
        driver.delete_all_cookies()
        driver.execute_cdp_cmd('Network.clearBrowserCache', {})
        driver.execute_cdp_cmd('Network.clearBrowserCookies', {})
        
        # Use the main URL without country prefix
        url = "https://888casino.com/live-casino/#filters=live-roulette"
        
        try:
            logging.info(f"Tentando acessar URL: {url} (tentativa {tentativa})")
            
            # Tentar acessar a página com retry
            for retry in range(3):
                try:
                    driver.get(url)
                    break
                except Exception as retry_error:
                    if retry < 2:  # Tentar mais 2 vezes antes de desistir
                        logging.warning(f"Erro ao carregar URL (retry {retry+1}): {str(retry_error)}")
                        time.sleep(5)
                    else:
                        raise
            
            # Aguardar carregamento inicial com timeout maior
            logging.info("Aguardando carregamento da página...")
            WebDriverWait(driver, 45).until(  # Aumentado para 45 segundos
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Esperar um pouco mais para garantir que a página carregue completamente
            time.sleep(10)  # Aumentado para 10 segundos
            
            if "888casino" in driver.current_url and "live-casino" in driver.current_url:
                logging.info(f"Sucesso ao acessar: {url}")
                return True
            else:
                logging.warning(f"URL incorreta após navegação: {driver.current_url}")
                raise Exception(f"URL incorreta após navegação: {driver.current_url}")
                
        except Exception as e:
            logging.error(f"Falha ao acessar {url}: {str(e)}")
            
            # Tentar capturar screenshot para debug
            try:
                screenshot_path = f"error_screenshot_{int(time.time())}.png"
                driver.save_screenshot(screenshot_path)
                logging.info(f"Screenshot salvo em: {screenshot_path}")
            except Exception as ss_error:
                logging.error(f"Não foi possível salvar screenshot: {str(ss_error)}")
                
            raise
        
    except Exception as e:
        logging.error(f"Erro ao navegar para o site (tentativa {tentativa}): {str(e)}")
        if tentativa < max_tentativas:
            # Aumentar o tempo de espera entre tentativas
            wait_time = 15 * tentativa  # 15, 30, 45 segundos...
            logging.info(f"Aguardando {wait_time} segundos antes da próxima tentativa...")
            time.sleep(wait_time)
            return navegar_para_site(driver, tentativa + 1, max_tentativas)
        else:
            raise Exception(f"Falha ao acessar o site após {max_tentativas} tentativas")

# Add this function to check memory without psutil
def check_memory_usage():
    """Monitor memory usage and force garbage collection if needed"""
    try:
        # Simple memory check using gc
        gc.collect()
        logging.info("Performed garbage collection")
        return 0  # We can't get actual memory usage without psutil
    except Exception as e:
        logging.error(f"Error during memory check: {str(e)}")
        return 0

def extrair_numeros():
    global driver, executando, numeros_roletas, analisadores_mesas
    
    # Contador para limitar redirecionamentos
    redirection_count = 0
    last_redirection_time = time.time()
    memory_check_time = time.time()
    
    while executando:
        try:
            # Verificar memória a cada 60 segundos
            current_time = time.time()
            if current_time - memory_check_time > 60:
                check_memory_usage()  # Call our simplified function
                memory_check_time = current_time
                
            # Verificar URL atual e redirecionar se necessário, mas com limitação
            current_url = driver.current_url
            current_time = time.time()
            
            if ("888casino.com" not in current_url or "live-casino" not in current_url) and \
               (current_time - last_redirection_time > 60 or redirection_count < 3):
                logging.warning("URL incorreta detectada, redirecionando...")
                driver.get("https://888casino.com/live-casino/#filters=live-roulette")
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
                    
                    # Extrair o ID da roleta da classe CSS
                    class_attribute = elemento.get_attribute("class")
                    id_roleta = None
                    
                    # Procurar pelo padrão cy-live-casino-grid-item-XXXXXXX ou game-type-XXXXXXX
                    import re
                    id_matches = re.findall(r'(cy-live-casino-grid-item-|game-type-)(\d+)', class_attribute)
                    if id_matches:
                        id_roleta = id_matches[0][1]  # Pegar o número após o prefixo
                    
                    # Verificar se a roleta está na lista de permitidas por ID
                    from config import roleta_permitida_por_id
                    
                    if id_roleta and not roleta_permitida_por_id(id_roleta):
                        # Silenciosamente ignorar roletas não permitidas sem log
                        continue
                    
                    # Log the roulette title for debugging
                    logging.info(f"Processando roleta: {titulo} (ID: {id_roleta})")
                    
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
                        
                        # Inicializar a mesa se for a primeira vez
                        if titulo not in numeros_roletas:
                            numeros_roletas[titulo] = {
                                "numeros": [],
                                "ultima_atualizacao": "",
                                "estrategia": {}
                            }
                            # Na primeira execução, processar todos os números disponíveis
                            for num in reversed(numeros_atuais):  # Processar do mais antigo para o mais recente
                                analisadores_mesas[titulo].process_number(num)
                                numeros_roletas[titulo]["numeros"].insert(0, num)  # Adicionar ao início da lista
                            
                            # Limitar a 20 números
                            numeros_roletas[titulo]["numeros"] = numeros_roletas[titulo]["numeros"][:20]
                            logging.info(f"Inicialização de {titulo} com {len(numeros_atuais)} números")
                        # Se já existe, verificar apenas o número mais recente
                        elif not numeros_anteriores or ultimo_numero != numeros_anteriores[0]:
                            logging.info(f"Novo número detectado para {titulo}: {ultimo_numero}")
                            
                            # Processar apenas o número mais recente na estratégia
                            analisadores_mesas[titulo].process_number(ultimo_numero)
                            
                            # Adicionar apenas o novo número ao início da lista e manter o limite
                            numeros_roletas[titulo]["numeros"].insert(0, ultimo_numero)
                            numeros_roletas[titulo]["numeros"] = numeros_roletas[titulo]["numeros"][:20]
                        
                        # Atualizar timestamp e status da estratégia
                        timestamp_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        numeros_roletas[titulo].update({
                            "ultima_atualizacao": timestamp_atual,
                            "estrategia": analisadores_mesas[titulo].get_status()
                        })
                        
                        # Enviar dados para o Firebase se o cliente estiver disponível
                        if firebase_client:
                            try:
                                # Enviar dados para o Firebase
                                firebase_client.send_roleta_data(titulo, numeros_roletas[titulo])
                                logging.info(f"Dados de {titulo} enviados para o Firebase")
                            except Exception as e:
                                logging.error(f"Erro ao enviar dados para o Firebase: {str(e)}")
                        
                        logging.info(f"Números atualizados para {titulo}: {numeros_roletas[titulo]['numeros']}")
                    else:
                        logging.warning(f"Nenhum número encontrado para a mesa {titulo} - aguardando próxima atualização")
                            
                except Exception as e:
                    logging.error(f"Erro ao processar roleta {titulo if 'titulo' in locals() else 'desconhecida'}: {str(e)}")
            
            # Delay aleatório entre verificações (similar ao código C#)
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
        if not firebase_client:
            return jsonify({
                'error': "Cliente Firebase não inicializado"
            }), 500
            
        roletas_ref = firebase_client.get_roletas_ref()
        dados_roletas = roletas_ref.get() or {}
        
        # Adicionar timestamp para debug
        for roleta in dados_roletas.values():
            if 'ultima_atualizacao' not in roleta:
                roleta['ultima_atualizacao'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        return jsonify(dados_roletas)
    except Exception as e:
        app.logger.error(f"Erro ao obter dados do Firebase: {str(e)}")
        return jsonify({
            'error': f"Falha ao conectar com Firebase: {str(e)}"
        }), 500

@app.route('/sync_firebase')
def sync_firebase():
    """Endpoint para sincronizar dados manualmente com o Firebase"""
    if firebase_client and numeros_roletas:
        try:
            result = firebase_client.send_all_roletas(numeros_roletas)
            if result:
                return jsonify({"status": "success", "message": "Dados sincronizados com o Firebase"})
            else:
                return jsonify({"status": "error", "message": "Falha ao sincronizar dados"})
        except Exception as e:
            return jsonify({"status": "error", "message": f"Erro ao sincronizar: {str(e)}"})
    else:
        return jsonify({"status": "warning", "message": "Firebase não disponível ou nenhum dado para sincronizar"})

@app.route('/test_firebase', methods=['GET'])
def test_firebase():
    """Testa a conexão com o Firebase."""
    global firebase_client
    
    try:
        # Verificar variáveis de ambiente disponíveis
        env_vars = {
            'FIREBASE_CREDENTIALS_JSON': 'Definido' if os.environ.get('FIREBASE_CREDENTIALS_JSON') else 'Não definido',
            'FIREBASE_CREDENTIALS_JSON_BASE64': 'Definido' if os.environ.get('FIREBASE_CREDENTIALS_JSON_BASE64') else 'Não definido',
            'FIREBASE_CREDS_FILE': os.environ.get('FIREBASE_CREDS_FILE', 'Não definido'),
            'DYNO': os.environ.get('DYNO', 'Não definido'),
            'PWD': os.environ.get('PWD', 'Não definido')
        }
        
        # Listar arquivos no diretório atual
        current_dir = os.path.dirname(os.path.abspath(__file__))
        files_in_dir = os.listdir(current_dir)
        
        if not firebase_client:
            # Tentar inicializar o Firebase novamente
            try:
                creds_file = find_credentials_file()
                if creds_file:
                    logging.info(f"Tentando inicializar Firebase com arquivo: {creds_file}")
                    # Verificar se o arquivo existe e tem conteúdo válido
                    if os.path.exists(creds_file):
                        with open(creds_file, 'r') as f:
                            creds_content = f.read()
                            logging.info(f"Conteúdo do arquivo de credenciais (primeiros 50 caracteres): {creds_content[:50]}...")
                    
                    firebase_client = FirebaseClient(creds_file)
                    logging.info(f"Cliente Firebase inicializado com sucesso no teste usando arquivo: {creds_file}")
                else:
                    logging.error("Arquivo de credenciais do Firebase não encontrado")
                    return jsonify({
                        'status': 'error',
                        'message': "Arquivo de credenciais do Firebase não encontrado",
                        'debug': {
                            'env_vars': env_vars,
                            'files_in_dir': files_in_dir,
                            'current_dir': current_dir
                        }
                    }), 500
            except Exception as e:
                logging.error(f"Erro ao inicializar Firebase: {str(e)}")
                return jsonify({
                    'status': 'error',
                    'message': f"Cliente Firebase não inicializado e falha ao inicializar: {str(e)}",
                    'traceback': str(sys.exc_info()),
                    'debug': {
                        'env_vars': env_vars,
                        'files_in_dir': files_in_dir,
                        'current_dir': current_dir
                    }
                }), 500
            
        # Tenta obter uma referência do Firebase
        try:
            ref = firebase_client.get_roletas_ref()
            logging.info("Referência do Firebase obtida com sucesso")
            
            # Tenta fazer uma operação simples de leitura
            test_data = ref.child('test_connection').get()
            logging.info(f"Leitura de teste realizada: {test_data}")
            
            # Se não existir, cria um registro de teste
            if test_data is None:
                ref.child('test_connection').set({
                    'timestamp': int(time.time()),
                    'status': 'ok'
                })
                test_data = {'status': 'ok', 'message': 'Registro de teste criado com sucesso'}
                logging.info("Registro de teste criado com sucesso")
            
            return jsonify({
                'status': 'success',
                'message': 'Conexão com Firebase estabelecida com sucesso',
                'data': test_data
            })
        except Exception as firebase_error:
            logging.error(f"Erro específico do Firebase: {str(firebase_error)}")
            return jsonify({
                'status': 'error',
                'message': f"Erro ao acessar Firebase: {str(firebase_error)}",
                'traceback': str(sys.exc_info())
            }), 500
    except Exception as e:
        logging.error(f"Erro geral ao testar conexão com Firebase: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Erro ao conectar com Firebase: {str(e)}",
            'traceback': str(sys.exc_info())
        }), 500

@app.route('/check_env', methods=['GET'])
def check_env():
    """Verifica as variáveis de ambiente disponíveis e tenta decodificar as credenciais Base64."""
    try:
        # Verificar variáveis de ambiente disponíveis
        env_vars = {
            'FIREBASE_CREDENTIALS_JSON': 'Definido' if os.environ.get('FIREBASE_CREDENTIALS_JSON') else 'Não definido',
            'FIREBASE_CREDENTIALS_JSON_BASE64': 'Definido' if os.environ.get('FIREBASE_CREDENTIALS_JSON_BASE64') else 'Não definido',
            'FIREBASE_CREDS_FILE': os.environ.get('FIREBASE_CREDS_FILE', 'Não definido'),
            'DYNO': os.environ.get('DYNO', 'Não definido'),
            'PWD': os.environ.get('PWD', 'Não definido')
        }
        
        # Verificar se o arquivo temporário foi criado
        temp_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_firebase_creds.json')
        file_exists = os.path.exists(temp_file)
        file_content = None
        
        if file_exists:
            try:
                with open(temp_file, 'r') as f:
                    file_content = f.read()[:100] + '...' if len(f.read()) > 100 else f.read()
            except Exception as e:
                file_content = f"Erro ao ler arquivo: {str(e)}"
        
        # Listar arquivos no diretório atual
        current_dir = os.path.dirname(os.path.abspath(__file__))
        files_in_dir = os.listdir(current_dir)
        
        # Tentar decodificar as credenciais Base64 para debug
        base64_debug = {}
        firebase_creds_base64 = os.environ.get('FIREBASE_CREDENTIALS_JSON_BASE64')
        if firebase_creds_base64:
            try:
                # Verificar se é uma string Base64 válida
                base64_debug['is_valid'] = True
                base64_debug['length'] = len(firebase_creds_base64)
                
                # Limpar e preparar a string Base64
                firebase_creds_base64 = firebase_creds_base64.strip()
                firebase_creds_base64 = firebase_creds_base64.replace('-', '+').replace('_', '/')
                padding = len(firebase_creds_base64) % 4
                if padding:
                    firebase_creds_base64 += '=' * (4 - padding)
                
                # Tentar decodificar
                try:
                    decoded_creds = base64.b64decode(firebase_creds_base64).decode('utf-8')
                    base64_debug['decoded_length'] = len(decoded_creds)
                    base64_debug['decoded_start'] = decoded_creds[:50] + '...'
                    base64_debug['is_json'] = True
                    
                    # Verificar se é um JSON válido
                    try:
                        json.loads(decoded_creds)
                    except json.JSONDecodeError:
                        base64_debug['is_json'] = False
                except Exception:
                    base64_debug['standard_b64decode_failed'] = True
                    try:
                        decoded_creds = base64.urlsafe_b64decode(firebase_creds_base64).decode('utf-8')
                        base64_debug['urlsafe_b64decode_success'] = True
                        base64_debug['decoded_length'] = len(decoded_creds)
                        base64_debug['decoded_start'] = decoded_creds[:50] + '...'
                    except Exception as e:
                        base64_debug['all_decoding_failed'] = True
                        base64_debug['error'] = str(e)
                    
            except Exception as e:
                base64_debug['is_valid'] = False
                base64_debug['error'] = str(e)
        
        return jsonify({
            'status': 'success',
            'env_vars': env_vars,
            'temp_file_exists': file_exists,
            'temp_file_content': file_content,
            'files_in_dir': files_in_dir,
            'current_dir': current_dir,
            'base64_debug': base64_debug,
            'write_permissions': os.access(current_dir, os.W_OK)
        })
    except Exception as e:
        logging.error(f"Erro ao verificar variáveis de ambiente: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Erro ao verificar variáveis de ambiente: {str(e)}",
            'traceback': str(sys.exc_info())
        }), 500

if __name__ == '__main__':
    # Obter porta do Heroku ou usar 5000 como padrão
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)