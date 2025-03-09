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
from flask import Flask, Response, request
from flask_cors import CORS
import threading
import queue

from config import CASINO_URL, SUPABASE_URL, SUPABASE_KEY, roleta_permitida_por_id, SCRAPE_INTERVAL_MINUTES, logger, MAX_CICLOS
from strategy_analyzer import StrategyAnalyzer

# Criar a aplicação Flask
app = Flask(__name__)
CORS(app)  # Habilitar CORS para permitir acesso a partir do frontend

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
        
        # Enviar para todos os clientes
        for client_queue in self.clients[:]:  # Copia para evitar problemas se a lista mudar
            try:
                client_queue.put(event_data)
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
        yield 'data: {"type": "connected", "message": "Conexão SSE estabelecida"}\n\n'
        
        try:
            while True:
                # Aguardar eventos na fila do cliente
                try:
                    event_data = client_queue.get(timeout=30)  # 30s timeout para heartbeat
                    yield f'data: {json.dumps(event_data)}\n\n'
                except queue.Empty:
                    # Enviar heartbeat para manter a conexão viva
                    yield 'event: ping\ndata: {}\n\n'
        except GeneratorExit:
            # Cliente desconectou
            event_manager.unregister_client(client_queue)
    
    return Response(generate(), mimetype='text/event-stream', 
                   headers={'Cache-Control': 'no-cache', 'Connection': 'keep-alive'})

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

# Dicionário global para manter os analisadores de cada mesa
analisadores_mesas = {}

def configurar_driver():
    """Configura o driver do Selenium com as opções apropriadas para o Heroku"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # No Heroku, o caminho do executável está em /app/.chromedriver/bin/chromedriver
    if 'DYNO' in os.environ:
        chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
        driver = webdriver.Chrome(
            executable_path=os.environ.get("CHROMEDRIVER_PATH"),
            options=chrome_options
        )
    else:
        # Para desenvolvimento local
        try:
            # Tenta usar o ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logger.error(f"Erro ao configurar ChromeDriverManager: {str(e)}")
            
            # Fallback: Tentar executável local ou especificado nas variáveis de ambiente
            if platform.system() == "Windows":
                chrome_driver_path = os.environ.get("CHROME_DRIVER_PATH", "./chromedriver.exe")
            else:
                chrome_driver_path = os.environ.get("CHROME_DRIVER_PATH", "./chromedriver")
            
            service = Service(chrome_driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
    
    return driver

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

def main():
    """Função principal"""
    try:
        # Verificar se a tabela roleta_numeros existe
        try:
            supabase.table("roleta_numeros").select("count").limit(1).execute()
            logger.info("Tabela roleta_numeros verificada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao verificar tabela roleta_numeros: {str(e)}")
            logger.error("A tabela roleta_numeros pode não existir. Verifique a configuração do banco de dados.")
            return
        
        logger.info("Iniciando scraper de roletas...")
        
        # Agendar o scraping conforme o intervalo configurado
        logger.info(f"Agendando scraping a cada {SCRAPE_INTERVAL_MINUTES} minutos")
        schedule.every(SCRAPE_INTERVAL_MINUTES).minutes.do(scrape_roletas)
        
        # Executar imediatamente uma vez
        scrape_roletas()
        
        # Loop principal para manter o agendamento
        while True:
            schedule.run_pending()
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Scraper interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro no scraper: {str(e)}")

if __name__ == "__main__":
    # Iniciar o scraper em um thread separado
    scraper_thread = threading.Thread(target=main)
    scraper_thread.daemon = True
    scraper_thread.start()
    
    # Iniciar o servidor Flask
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
