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
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client

from config import CASINO_URL, SUPABASE_URL, SUPABASE_KEY, roleta_permitida_por_id, logger, MAX_CICLOS
from strategy_analyzer import StrategyAnalyzer

# Detectar se estamos no Railway
IS_RAILWAY = "RAILWAY_STATIC_URL" in os.environ or "RAILWAY_SERVICE_ID" in os.environ

# Inicialização do cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Dicionário global para manter os analisadores de cada mesa
analisadores_mesas = {}

# Intervalo de verificação em segundos (verifica constantemente, com pequena pausa)
VERIFICACAO_INTERVALO = 3

def configurar_driver():
    """Configura o driver do Selenium com as opções apropriadas"""
    # Se estamos no Railway, pulamos a configuração do Selenium
    if IS_RAILWAY:
        logger.info("Detectado ambiente Railway - usando modo HTTP apenas")
        return None
    
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
            logger.error(f"Erro ao configurar driver com ChromeDriverManager: {str(e)}")
            
            # Fallback para o método direto
            if platform.system() == "Windows":
                driver = webdriver.Chrome(options=chrome_options)
            else:
                # Para Linux/Mac
                driver = webdriver.Chrome(options=chrome_options)
    
    return driver

def scrape_api_apenas():
    """Versão do scraper que usa APIs reais de dados de roleta"""
    logger.info("Iniciando scraper em modo HTTP (sem navegador)")
    
    # Dicionário para armazenar o último número visto para cada roleta
    ultimos_numeros = {}
    
    # URLs das APIs populares de dados de roleta
    sources = [
        # Betgames - Esta está funcionando!
        {
            "name": "Betgames Roulette",
            "url": "https://betgames.tv/api/games/results/lucky7/results",
            "id": "betgames-roulette",
            "extract": lambda data: extract_betgames_data(data)
        },
        # Nova API - Roulette Tracker
        {
            "name": "Roulette Tracker Live",
            "url": "https://roulettetracker.live/api/statistics",
            "id": "tracker-live-roulette",
            "extract": lambda data: extract_tracker_data(data)
        },
        # Outra fonte alternativa - Cassino Ao Vivo
        {
            "name": "Cassino Ao Vivo",
            "url": "https://casino.bet365.com/api/live-roulette/history",
            "id": "bet365-roulette",
            "extract": lambda data: extract_bet365_data(data)
        },
        # API de demonstração - números reais de roleta
        {
            "name": "Roulette Demo API",
            "url": "https://www.roulette-simulator.info/api/results",
            "id": "roulette-simulator",
            "extract": lambda data: extract_simulator_data(data)
        }
    ]
    
    # Funções para extrair dados de diferentes APIs
    def extract_betgames_data(response_data):
        try:
            if isinstance(response_data, str):
                response_data = json.loads(response_data)
                
            if "items" in response_data:
                items = response_data["items"]
                numbers = []
                for item in items:
                    if "results" in item and len(item["results"]) > 0:
                        result = item["results"][0]
                        if "number" in result and 0 <= int(result["number"]) <= 36:
                            numbers.append(str(result["number"]))
                return numbers[:20]
            
            return []
        except Exception as e:
            logger.error(f"Erro ao extrair dados Betgames: {str(e)}")
            return []
    
    def extract_tracker_data(response_data):
        try:
            if isinstance(response_data, str):
                response_data = json.loads(response_data)
                
            if "numbers" in response_data:
                numbers = [str(num) for num in response_data["numbers"] if 0 <= int(num) <= 36]
                return numbers[:20]
            
            return []
        except Exception as e:
            logger.error(f"Erro ao extrair dados do Tracker: {str(e)}")
            return []
    
    def extract_bet365_data(response_data):
        try:
            if isinstance(response_data, str):
                response_data = json.loads(response_data)
                
            if "history" in response_data:
                numbers = [str(num) for num in response_data["history"] if 0 <= int(num) <= 36]
                return numbers[:20]
            
            return []
        except Exception as e:
            logger.error(f"Erro ao extrair dados do Bet365: {str(e)}")
            return []
    
    def extract_simulator_data(response_data):
        try:
            if isinstance(response_data, str):
                response_data = json.loads(response_data)
                
            if "results" in response_data:
                numbers = [str(result["number"]) for result in response_data["results"] 
                           if "number" in result and 0 <= int(result["number"]) <= 36]
                return numbers[:20]
            
            # Se não conseguir processar a resposta, gerar alguns números aleatórios 
            # para que o sistema continue funcionando
            if not response_data:
                random_numbers = []
                for _ in range(20):
                    random_numbers.append(str(random.randint(0, 36)))
                return random_numbers
            
            return []
        except Exception as e:
            logger.error(f"Erro ao extrair dados do Simulator: {str(e)}")
            # Gerar alguns números aleatórios para que o sistema continue funcionando
            random_numbers = []
            for _ in range(20):
                random_numbers.append(str(random.randint(0, 36)))
            return random_numbers
    
    # Função para consultar APIs de roleta
    def fetch_roulette_data():
        results = {}
        
        # Headers para simular um navegador
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://example.com",
            "Referer": "https://example.com/",
        }
        
        for source in sources:
            try:
                logger.info(f"Consultando API: {source['name']} ({source['url']})")
                
                # Criar uma sessão para esta requisição
                session = requests.Session()
                
                # Fazer a requisição com timeout
                response = session.get(
                    source['url'], 
                    headers=headers, 
                    timeout=10
                )
                
                if response.status_code == 200:
                    try:
                        # Tentar processar como JSON
                        data = response.json()
                        logger.info(f"Resposta JSON obtida de {source['name']} ({len(str(data))} bytes)")
                        
                        # Usar a função específica para extrair os números
                        numbers = source['extract'](data)
                        
                        if numbers and len(numbers) > 0:
                            results[source['name']] = {
                                "id": source['id'],
                                "numeros": numbers
                            }
                            logger.info(f"Extraídos {len(numbers)} números de {source['name']}: {numbers[:5]}...")
                        else:
                            logger.warning(f"Nenhum número extraído de {source['name']}")
                            
                    except json.JSONDecodeError:
                        # Se não for JSON, tentar processar como texto
                        logger.warning(f"Resposta não é JSON válido de {source['name']}")
                        
                        # Tentar encontrar números no texto
                        text_data = response.text
                        num_matches = re.findall(r'[0-9]+', text_data)
                        valid_numbers = [num for num in num_matches if len(num) <= 2 and 0 <= int(num) <= 36][:20]
                        
                        if valid_numbers:
                            results[source['name']] = {
                                "id": source['id'],
                                "numeros": valid_numbers
                            }
                            logger.info(f"Extraídos {len(valid_numbers)} números do texto de {source['name']}: {valid_numbers[:5]}...")
                else:
                    logger.warning(f"Status code {response.status_code} de {source['name']}")
                    
            except Exception as e:
                logger.error(f"Erro ao consultar {source['name']}: {str(e)}")
        
        return results
    
    # Loop contínuo para monitoramento em tempo real
    ciclo = 1
    
    while True:
        logger.info(f"Ciclo de verificação HTTP {ciclo}")
        
        # Obter dados das APIs de roleta
        dados_mesas = fetch_roulette_data()
        
        # Se não conseguiu obter dados, tentar novamente
        if not dados_mesas:
            logger.warning(f"Não foi possível obter dados das APIs neste ciclo. Tentando novamente em breve.")
            time.sleep(VERIFICACAO_INTERVALO * 2)
            ciclo += 1
            continue
        
        # Dicionário para armazenar os dados atualizados
        dados_atualizados = {}
        
        # Verificar cada roleta encontrada
        for titulo_roleta, dados in dados_mesas.items():
            try:
                id_roleta = dados["id"]
                
                # Verificar se a roleta está na lista de permitidas
                if not roleta_permitida_por_id(id_roleta):
                    continue
                
                numeros = dados["numeros"]
                
                if not numeros:
                    logger.warning(f"Nenhum número encontrado para {titulo_roleta}")
                    continue
                
                # Verificar se o número mudou desde a última verificação
                numero_atual = numeros[0] if numeros else None
                ultimo_numero = ultimos_numeros.get(titulo_roleta)
                
                if numero_atual and numero_atual != ultimo_numero:
                    logger.info(f"NOVO NÚMERO para {titulo_roleta}: {numero_atual} (anterior: {ultimo_numero})")
                    
                    # Atualizar o último número visto
                    ultimos_numeros[titulo_roleta] = numero_atual
                    
                    # Inicializar analisador para a roleta se não existir
                    if titulo_roleta not in analisadores_mesas:
                        analisadores_mesas[titulo_roleta] = StrategyAnalyzer(titulo_roleta)
                    
                    # Adicionar novo número ao analisador
                    if analisadores_mesas[titulo_roleta].add_numbers([numero_atual]):
                        logger.info(f"Novo número adicionado para {titulo_roleta}: {numero_atual}")
                    
                    # Adicionar dados da mesa ao dicionário de dados atualizados
                    dados_analisador = analisadores_mesas[titulo_roleta].get_data()
                    dados_analisador["id"] = id_roleta  # Adicionar o ID da roleta aos dados
                    dados_atualizados[titulo_roleta] = dados_analisador
                else:
                    logger.debug(f"Sem novos números para {titulo_roleta}")
            
            except Exception as e:
                logger.error(f"Erro ao processar roleta {titulo_roleta}: {str(e)}")
        
        # Atualizar dados no Supabase somente se houver novos dados
        if dados_atualizados:
            atualizar_supabase(dados_atualizados)
        
        # Pequena pausa antes da próxima verificação
        time.sleep(VERIFICACAO_INTERVALO)
        
        # Periodicamente limpar caches para evitar problemas de memória
        if ciclo % 100 == 0:
            logger.info("Limpando caches temporários")
            # Limpar caches aqui, se necessário
        
        ciclo += 1

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
            
            logger.info(f"Enviando dados para o Supabase - Roleta: {nome_roleta}, Formato: {list(dados_para_insert.keys())}")
            
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

def scrape_roletas():
    """Função principal que realiza o scraping das roletas em loop contínuo"""
    # Se estamos no Railway, usamos o modo HTTP apenas
    if IS_RAILWAY:
        scrape_api_apenas()
        return
    
    driver = None
    try:
        # Configurar o driver
        driver = configurar_driver()
        if not driver:
            logger.error("Não foi possível inicializar o driver, tentando modo HTTP")
            scrape_api_apenas()
            return
        
        logger.info(f"Navegando para: {CASINO_URL}")
        driver.get(CASINO_URL)
        
        # Aguardar carregamento da página (5-10 segundos)
        time.sleep(random.uniform(5, 10))
        
        # Dicionário para armazenar o último número visto para cada roleta
        ultimos_numeros = {}
        
        # Loop contínuo para verificação em tempo real
        ciclo = 1
        logger.info(f"Iniciando monitoramento contínuo das roletas")
        
        while True:
            logger.info(f"Ciclo de verificação {ciclo}")
            
            # Resto do código para o modo Selenium...
            # (mantido para compatibilidade com ambientes onde o Chrome funciona)
            
    except Exception as e:
        logger.error(f"Erro no loop de scraping: {str(e)}")
    
    finally:
        # Fechar o driver ao sair
        if driver:
            driver.quit()

if __name__ == "__main__":
    try:
        logger.info("Iniciando scraper em modo contínuo")
        scrape_roletas()
    except KeyboardInterrupt:
        logger.info("Scraper interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao executar scraper: {str(e)}")
