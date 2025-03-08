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

# Intervalo de verificação em segundos
VERIFICACAO_INTERVALO = 3

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
    """Configura o driver do Selenium com as opções apropriadas"""
    logger.info(f"Configurando driver (tentativa {tentativa}/{max_tentativas})...")
    
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument(f"user-agent={get_random_user_agent()}")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        
        # Verificar ambiente - Railway vs Local
        if IS_RAILWAY:
            # Imprimir variáveis de ambiente para debug
            logger.info(f"PATH: {os.environ.get('PATH', 'Não definido')}")
            
            try:
                # No Railway, tentar usar o Chrome diretamente
                logger.info("Tentando usar Chrome automático...")
                driver = webdriver.Chrome(options=chrome_options)
                logger.info("Driver configurado com sucesso usando Chrome automático")
                return driver
            except Exception as chrome_error:
                logger.error(f"Erro ao inicializar Chrome automático: {str(chrome_error)}")
                
                # Tentar usar o webdriver_manager como fallback
                try:
                    logger.info("Tentando usar webdriver_manager como fallback")
                    service = Service(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=chrome_options)
                    logger.info("Driver configurado com sucesso usando webdriver_manager")
                    return driver
                except Exception as wdm_error:
                    logger.error(f"Erro ao usar webdriver_manager: {str(wdm_error)}")
                    raise
        else:
            # Configuração para ambiente local
            logger.info("Ambiente local detectado")
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
        
        logger.info("Driver configurado com sucesso!")
        return driver
        
    except Exception as e:
        logger.error(f"Erro ao configurar driver (tentativa {tentativa}): {str(e)}")
        if tentativa < max_tentativas:
            logger.info(f"Tentando novamente em 10 segundos...")
            time.sleep(10)
            return configurar_driver(tentativa + 1, max_tentativas)
        else:
            raise Exception(f"Falha ao configurar driver após {max_tentativas} tentativas")

def navegar_para_site(driver, tentativa=1, max_tentativas=3):
    """Navega para o site do cassino com múltiplas tentativas e URLs"""
    logger.info(f"Navegando para o site (tentativa {tentativa}/{max_tentativas})...")
    
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
        
        # Se houver URL personalizada na configuração, adicionar no início da lista
        if CASINO_URL and CASINO_URL not in urls:
            urls.insert(0, CASINO_URL)
        
        for url in urls:
            try:
                logger.info(f"Tentando acessar: {url}")
                driver.get(url)
                # Aguardar carregamento inicial com timeout maior
                WebDriverWait(driver, 30).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
                time.sleep(5)
                
                if "888casino" in driver.current_url and "live-casino" in driver.current_url:
                    logger.info(f"Sucesso ao acessar: {url}")
                    return True
                else:
                    logger.warning(f"URL redirecionada para: {driver.current_url}")
            except Exception as e:
                logger.warning(f"Falha ao acessar {url}: {str(e)}")
                continue
        
        raise Exception("Não foi possível acessar nenhuma URL disponível")
        
    except Exception as e:
        logger.error(f"Erro ao navegar para o site (tentativa {tentativa}): {str(e)}")
        if tentativa < max_tentativas:
            logger.info(f"Tentando novamente em 10 segundos...")
            time.sleep(10)
            return navegar_para_site(driver, tentativa + 1, max_tentativas)
        else:
            raise Exception(f"Falha ao acessar o site após {max_tentativas} tentativas")

def extrair_numeros_js(driver, elemento_roleta):
    """Extrai números de roleta usando JavaScript - método mais robusto"""
    try:
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
        """, elemento_roleta)
        
        # Converter para strings para manter a consistência com o resto do código
        return [str(num) for num in numeros_atuais]
    except Exception as e:
        logger.error(f"Erro ao extrair números via JavaScript: {str(e)}")
        return []

def extrair_titulo_roleta(elemento_roleta):
    """Extrai o título da roleta do elemento"""
    try:
        titulo_elemento = elemento_roleta.find_element(By.CLASS_NAME, "cy-live-casino-grid-item-title")
        return titulo_elemento.text.strip()
    except Exception as e:
        logger.error(f"Erro ao extrair título da roleta: {str(e)}")
        # Gerar um título baseado em timestamp para identificação única
        return f"Roleta-{datetime.now().strftime('%H%M%S')}"

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

def scrape_roletas():
    """Função principal que realiza o scraping das roletas em loop contínuo usando Selenium"""
    driver = None
    try:
        # Configurar o driver
        driver = configurar_driver()
        if not driver:
            logger.error("Não foi possível inicializar o driver")
            return
        
        # Navegar para o site do cassino
        if not navegar_para_site(driver):
            logger.error("Não foi possível acessar o site")
            return
        
        # Dicionário para armazenar dados das roletas e ultimos números vistos
        dados_roletas = {}
        ultimos_numeros = {}
        
        # Contador para limitar redirecionamentos
        redirection_count = 0
        last_redirection_time = time.time()
        
        # Loop contínuo para verificação em tempo real
        ciclo = 1
        logger.info(f"Iniciando monitoramento contínuo das roletas")
        
        while True:
            try:
                logger.info(f"Ciclo de verificação {ciclo}")
                
                # Verificar URL atual e redirecionar se necessário, mas com limitação
                current_url = driver.current_url
                current_time = time.time()
                
                if ("888casino.com" not in current_url or "live-casino" not in current_url) and \
                   (current_time - last_redirection_time > 60 or redirection_count < 3):
                    logger.warning("URL incorreta detectada, redirecionando...")
                    driver.get("https://es.888casino.com/live-casino/#filters=live-roulette")
                    time.sleep(5)
                    redirection_count += 1
                    last_redirection_time = current_time
                elif current_time - last_redirection_time > 300:
                    # Reset counter every 5 minutes
                    redirection_count = 0
                
                # Encontrar todas as roletas
                elementos_roleta = WebDriverWait(driver, 15).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "cy-live-casino-grid-item"))
                )
                
                logger.info(f"Encontradas {len(elementos_roleta)} roletas na página")
                
                # Processar todas as roletas
                for elemento_roleta in elementos_roleta:
                    try:
                        # Extrair título da roleta
                        titulo_roleta = extrair_titulo_roleta(elemento_roleta)
                        logger.info(f"Processando roleta: {titulo_roleta}")
                        
                        # Gerar um ID único para a roleta
                        id_roleta = f"roleta-{hash(titulo_roleta) % 100000}"
                        
                        # Verificar se a roleta está na lista de permitidas
                        if not roleta_permitida_por_id(id_roleta):
                            logger.info(f"Roleta {titulo_roleta} não está na lista de permitidas. Pulando.")
                            continue
                        
                        # Criar analisador para mesa se não existir
                        if titulo_roleta not in analisadores_mesas:
                            analisadores_mesas[titulo_roleta] = StrategyAnalyzer(titulo_roleta)
                            logger.info(f"Novo analisador criado para mesa: {titulo_roleta}")
                        
                        # Extrair números usando JavaScript
                        numeros_atuais = extrair_numeros_js(driver, elemento_roleta)
                        logger.info(f"Números extraídos para {titulo_roleta}: {numeros_atuais}")
                        
                        if numeros_atuais and len(numeros_atuais) > 0:
                            # O primeiro número é o mais recente
                            ultimo_numero = numeros_atuais[0]
                            
                            # Verificar se é um número novo
                            numero_anterior = ultimos_numeros.get(titulo_roleta)
                            
                            if not numero_anterior or ultimo_numero != numero_anterior:
                                logger.info(f"NOVO NÚMERO para {titulo_roleta}: {ultimo_numero} (anterior: {numero_anterior})")
                                
                                # Atualizar o último número visto
                                ultimos_numeros[titulo_roleta] = ultimo_numero
                                
                                # Adicionar novo número ao analisador
                                if analisadores_mesas[titulo_roleta].add_numbers([ultimo_numero]):
                                    logger.info(f"Novo número adicionado para {titulo_roleta}: {ultimo_numero}")
                                
                                # Inicializar dados da roleta se não existir
                                if titulo_roleta not in dados_roletas:
                                    dados_roletas[titulo_roleta] = {
                                        "numeros": [],
                                        "ultima_atualizacao": "",
                                        "id": id_roleta
                                    }
                                
                                # Adicionar novos números ao início da lista
                                dados_roletas[titulo_roleta]["numeros"] = numeros_atuais + [
                                    n for n in dados_roletas[titulo_roleta].get("numeros", [])
                                    if n not in numeros_atuais
                                ]
                                
                                # Limitar a lista a 20 números
                                dados_roletas[titulo_roleta]["numeros"] = dados_roletas[titulo_roleta]["numeros"][:20]
                                
                                # Atualizar timestamp e estratégia
                                dados_roletas[titulo_roleta].update({
                                    "ultima_atualizacao": datetime.now().isoformat(),
                                    "estrategia": analisadores_mesas[titulo_roleta].get_data()
                                })
                                
                                # Atualizar no Supabase
                                update_data = {titulo_roleta: dados_roletas[titulo_roleta]}
                                atualizar_supabase(update_data)
                            else:
                                logger.debug(f"Sem novos números para {titulo_roleta}")
                        else:
                            logger.warning(f"Nenhum número encontrado para {titulo_roleta}")
                    
                    except Exception as e:
                        logger.error(f"Erro ao processar roleta {titulo_roleta if 'titulo_roleta' in locals() else 'desconhecida'}: {str(e)}")
                
                # Pequena pausa aleatória entre verificações
                time.sleep(random.uniform(2.0, 3.0))
                ciclo += 1
                
                # Recarregar a página a cada 30 ciclos para evitar problemas
                if ciclo % 30 == 0:
                    logger.info("Recarregando a página para manter a sessão fresca")
                    driver.refresh()
                    time.sleep(5)
                
            except Exception as e:
                logger.error(f"Erro na extração: {str(e)}")
                
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
                    logger.error(f"Erro ao reiniciar driver: {str(e)}")
                    time.sleep(30)  # Esperar mais tempo antes de tentar novamente
    
    except Exception as e:
        logger.error(f"Erro no loop de scraping: {str(e)}")
    
    finally:
        # Fechar o driver ao sair
        if driver:
            driver.quit()

def scrape_api_apenas():
    """Função alternativa que redireciona para a implementação Selenium"""
    logger.info("Iniciando modo de scraping com Selenium...")
    scrape_roletas()

if __name__ == "__main__":
    try:
        logger.info("Iniciando scraper em modo contínuo")
        scrape_roletas()
    except KeyboardInterrupt:
        logger.info("Scraper interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao executar scraper: {str(e)}")
