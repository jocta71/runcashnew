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

from config import CASINO_URL, SUPABASE_URL, SUPABASE_KEY, roleta_permitida_por_id, SCRAPE_INTERVAL_MINUTES, logger, MAX_CICLOS
from strategy_analyzer import StrategyAnalyzer

# Inicialização do cliente Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
            logger.error(f"Erro ao configurar driver com ChromeDriverManager: {str(e)}")
            
            # Fallback para o método direto
            if platform.system() == "Windows":
                driver = webdriver.Chrome(options=chrome_options)
            else:
                # Para Linux/Mac
                driver = webdriver.Chrome(options=chrome_options)
    
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
                "terminais_gatilho": estrategia_data.get("terminais_gatilho", []),
                "terminais_gatilho_anterior": estrategia_data.get("terminais_gatilho_anterior", []),
                "vitorias": estrategia_data.get("vitorias", 0),
                "derrotas": estrategia_data.get("derrotas", 0),
                "sugestao_display": estrategia_data.get("sugestao_display", "")
            }
            
            # Atualizar os dados no Supabase
            response = supabase.table("roletas").upsert(registro).execute()
            
            logger.info(f"Dados atualizados para roleta '{nome_roleta}' (ID: {id_roleta})")
        
        return True
    
    except Exception as e:
        logger.error(f"Erro ao atualizar dados no Supabase: {str(e)}")
        return False

def scrape_roletas(driver=None):
    """Função principal que realiza o scraping das roletas"""
    driver_interno = driver
    try:
        # Configurar o driver apenas se não foi fornecido externamente
        if not driver_interno:
            driver_interno = configurar_driver()
            if not driver_interno:
                logger.error("Não foi possível inicializar o driver")
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
                    
                    logger.info(f"Processando roleta: {titulo_roleta} (ID: {id_roleta})")
                    
                    # Inicializar analisador para a roleta se não existir
                    if titulo_roleta not in analisadores_mesas:
                        analisadores_mesas[titulo_roleta] = StrategyAnalyzer(titulo_roleta)
                    
                    # Extrair números da roleta
                    numeros = extrair_numeros_js(driver_interno, elemento_roleta)
                    
                    # Adicionar números ao analisador
                    if analisadores_mesas[titulo_roleta].add_numbers(numeros):
                        logger.info(f"Novos números adicionados para {titulo_roleta}: {numeros}")
                    
                    # Adicionar dados da mesa ao dicionário de dados atualizados
                    dados = analisadores_mesas[titulo_roleta].get_data()
                    dados["id"] = id_roleta  # Adicionar o ID da roleta aos dados
                    dados_atualizados[titulo_roleta] = dados
                
                except Exception as e:
                    logger.error(f"Erro ao processar roleta: {str(e)}")
            
            # Atualizar dados no Supabase
            if dados_atualizados:
                atualizar_supabase(dados_atualizados)
            
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
        # Não fechar o driver em caso de erro, apenas retorná-lo
        return driver_interno
    
    # Retornar o driver em vez de fechá-lo
    return driver_interno

def main():
    """Função principal que executa o scraping continuamente"""
    logger.info("Iniciando aplicação de scraping")
    
    # Configurar o driver uma única vez
    driver = configurar_driver()
    if not driver:
        logger.error("Não foi possível inicializar o driver")
        return
    
    try:
        # Executar scraping em loop contínuo
        while True:
            # Passar o driver para a função de scraping
            driver = scrape_roletas(driver)
            
            # Se o driver for None, algo deu errado e precisamos reconfigurá-lo
            if not driver:
                logger.info("Reconfigurando o driver...")
                driver = configurar_driver()
                if not driver:
                    logger.error("Não foi possível reinicializar o driver")
                    break
    
    except KeyboardInterrupt:
        logger.info("Scraping interrompido pelo usuário")
    finally:
        # Fechar o driver apenas quando o programa inteiro terminar
        if driver:
            driver.quit()
            logger.info("Driver fechado")

if __name__ == "__main__":
    import os  # Para verificar variáveis de ambiente
    main()
