import time
import random
import re
import json
import os
import platform
from datetime import datetime
import logging
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from supabase import create_client

from config import CASINO_URL, SUPABASE_URL, SUPABASE_KEY, roleta_permitida_por_id, logger, MAX_CICLOS, CASINO_API_URLS
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
        logger.info("Detectado ambiente Railway - usando modo API apenas")
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

def extrair_numeros_js(driver, elemento_roleta):
    """Extrai apenas o número mais recente (no topo) da roleta"""
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
        
        # Método 4: Tentar obter a partir do atributo de dados
        dados_attr = elemento_roleta.get_attribute("data-results") or elemento_roleta.get_attribute("data-last-results")
        if dados_attr:
            try:
                dados_json = json.loads(dados_attr)
                if isinstance(dados_json, list) and dados_json:
                    numero = str(dados_json[0])
                    logger.info(f"Número extraído (método 4): {numero}")
                    return [numero]
            except json.JSONDecodeError:
                pass
    
    except (NoSuchElementException, Exception) as e:
        logger.warning(f"Erro ao extrair números: {str(e)}")
    
    logger.warning("Nenhum número foi extraído usando os métodos disponíveis")
    return []

def extrair_id_roleta(elemento_roleta):
    """Extrai o ID único da roleta a partir das classes do elemento"""
    try:
        classes = elemento_roleta.get_attribute("class")
        
        # Padrão 1: cy-live-casino-grid-item-123456
        match = re.search(r'cy-live-casino-grid-item-(\d+)', classes)
        if match:
            id_roleta = match.group(1)
            return id_roleta
        
        # Padrão 2: game-type-123456
        match = re.search(r'game-type-(\d+)', classes)
        if match:
            id_roleta = match.group(1)
            return id_roleta
        
        # ID padrão usando o texto do título se não encontrar ID específico
        titulo = elemento_roleta.find_element(By.CSS_SELECTOR, ".cy-live-casino-grid-item-title").text
        id_hash = f"unknown-{hash(titulo) % 10000}"
        return id_hash
    
    except Exception as e:
        logger.warning(f"Erro ao extrair ID da roleta: {str(e)}")
        return "unknown"

def atualizar_supabase(dados_roletas):
    """Atualiza os dados no Supabase"""
    try:
        # Verificar se a tabela existe
        supabase.table("roletas").select("count").limit(1).execute()
        
        # Para cada roleta, criar ou atualizar seu registro
        for nome_roleta, dados in dados_roletas.items():
            # Extrair o ID da roleta dos dados (se disponível) ou gerar um ID baseado no nome
            id_roleta = dados.get("id", f"roleta-{hash(nome_roleta) % 10000}")
            
            # Extrair dados da estratégia
            estrategia_data = dados.get("estrategia", {})
            
            # Garantir que vitórias e derrotas são números inteiros válidos
            vitorias = int(estrategia_data.get("vitorias", 0))
            derrotas = int(estrategia_data.get("derrotas", 0))
            
            # Preparar os dados para inserção
            registro = {
                "id": id_roleta,
                "nome": nome_roleta,
                "numeros": dados.get("numeros", []),
                "updated_at": datetime.now().isoformat(),
                # Adicionar campos da estratégia
                "estado_estrategia": estrategia_data.get("estado", "NEUTRAL"),
                "numero_gatilho": estrategia_data.get("numero_gatilho", -1),
                "numero_gatilho_anterior": estrategia_data.get("numero_gatilho_anterior", -1),
                "terminais_gatilho": estrategia_data.get("terminais_gatilho", [])[:3],  # Garantir apenas 3 números
                "terminais_gatilho_anterior": estrategia_data.get("terminais_gatilho_anterior", [])[:3],  # Garantir apenas 3 números
                "vitorias": vitorias,
                "derrotas": derrotas,
                "sugestao_display": estrategia_data.get("sugestao_display", "")
            }
            
            # Depuração para verificar os dados
            logger.info(f"Enviando para o Supabase - Roleta: {nome_roleta}, Vitórias: {vitorias}, Derrotas: {derrotas}")
            logger.info(f"Sugestão Display: {registro['sugestao_display']}")
            
            # Atualizar os dados no Supabase
            response = supabase.table("roletas").upsert(registro).execute()
            
            logger.info(f"Dados atualizados para roleta '{nome_roleta}' (ID: {id_roleta})")
        
        return True
    
    except Exception as e:
        logger.error(f"Erro ao atualizar dados no Supabase: {str(e)}")
        return False

def scrape_api_apenas():
    """Versão do scraper que usa requisições HTTP diretas para obter dados reais"""
    logger.info("Iniciando scraper em modo API (sem navegador)")
    
    # Definir alguns headers para parecer um navegador real
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": CASINO_URL,
        "Origin": CASINO_URL
    }
    
    # Usar os endpoints definidos na configuração
    roleta_endpoints = CASINO_API_URLS
    
    # Função para extrair dados de uma roleta específica
    def obter_dados_roleta(nome_roleta, endpoint_url):
        try:
            logger.info(f"Obtendo dados para {nome_roleta} de {endpoint_url}")
            response = requests.get(endpoint_url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                logger.error(f"Erro ao obter dados da roleta {nome_roleta}: Status {response.status_code}")
                return None
                
            dados = response.json()
            return dados
        except Exception as e:
            logger.error(f"Exceção ao obter dados da roleta {nome_roleta}: {str(e)}")
            return None
    
    # Dicionário para armazenar o último número visto para cada roleta
    ultimos_numeros = {}
    
    # Loop contínuo para monitoramento em tempo real
    ciclo = 1
    while True:
        logger.info(f"Ciclo de verificação API {ciclo}")
        
        # Dicionário para armazenar os dados atualizados
        dados_atualizados = {}
        
        # Verificar cada roleta registrada
        for titulo_roleta, endpoint in roleta_endpoints.items():
            try:
                # Obter dados da API real
                dados_api = obter_dados_roleta(titulo_roleta, endpoint)
                
                # Se não conseguiu obter dados, pular esta roleta
                if not dados_api:
                    continue
                
                # Extrair informações relevantes (ajuste conforme a estrutura real da API)
                id_roleta = dados_api.get("id", f"roleta-{hash(titulo_roleta) % 10000}")
                
                # Verificar se a roleta está na lista de permitidas
                if not roleta_permitida_por_id(id_roleta):
                    continue
                
                # Extrair os números da roleta (ajuste conforme a estrutura real da API)
                numeros = dados_api.get("numeros", [])
                
                if not numeros:
                    logger.warning(f"Nenhum número encontrado para {titulo_roleta}")
                    continue
                
                # Verificar se o número mudou desde a última verificação
                numero_atual = str(numeros[0]) if numeros else None
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

def scrape_roletas():
    """Função principal que realiza o scraping das roletas em loop contínuo"""
    # Se estamos no Railway, usamos o modo API apenas
    if IS_RAILWAY:
        scrape_api_apenas()
        return
    
    driver = None
    try:
        # Configurar o driver
        driver = configurar_driver()
        if not driver:
            logger.error("Não foi possível inicializar o driver, tentando modo API")
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
            
            # Encontrar todas as roletas na página
            elementos_roletas = driver.find_elements(By.CSS_SELECTOR, ".cy-live-casino-grid-item")
            
            # Dicionário para armazenar os dados atualizados
            dados_atualizados = {}
            
            # Processar cada roleta
            for elemento_roleta in elementos_roletas:
                try:
                    # Extrair título da roleta
                    titulo_elemento = elemento_roleta.find_element(By.CSS_SELECTOR, ".cy-live-casino-grid-item-title")
                    titulo_roleta = titulo_elemento.text.strip()
                    
                    # Extrair ID da roleta
                    id_roleta = extrair_id_roleta(elemento_roleta)
                    
                    # Verificar se a roleta está na lista de permitidas
                    if not roleta_permitida_por_id(id_roleta):
                        continue
                    
                    # Extrair o número mais recente
                    numeros = extrair_numeros_js(driver, elemento_roleta)
                    
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
                        if analisadores_mesas[titulo_roleta].add_numbers(numeros):
                            logger.info(f"Novo número adicionado para {titulo_roleta}: {numeros}")
                        
                        # Adicionar dados da mesa ao dicionário de dados atualizados
                        dados = analisadores_mesas[titulo_roleta].get_data()
                        dados["id"] = id_roleta  # Adicionar o ID da roleta aos dados
                        dados_atualizados[titulo_roleta] = dados
                    else:
                        logger.debug(f"Sem novos números para {titulo_roleta}")
                
                except Exception as e:
                    logger.error(f"Erro ao processar roleta: {str(e)}")
            
            # Atualizar dados no Supabase somente se houver novos dados
            if dados_atualizados:
                atualizar_supabase(dados_atualizados)
            
            # Pequena pausa antes da próxima verificação
            time.sleep(VERIFICACAO_INTERVALO)
            
            # Recarregar a página a cada 30 ciclos para evitar problemas de memória
            if ciclo % 30 == 0:
                logger.info("Recarregando a página para manter a sessão fresca")
                driver.refresh()
                time.sleep(5)
            
            ciclo += 1
        
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
