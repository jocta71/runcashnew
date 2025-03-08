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
    """Versão do scraper que usa requisições HTTP diretas para obter dados do site"""
    logger.info("Iniciando scraper em modo HTTP (sem navegador)")
    
    # Dicionário para armazenar o último número visto para cada roleta
    ultimos_numeros = {}
    
    # Função para extrair dados da página
    def extrair_dados_da_pagina():
        try:
            url = CASINO_URL.strip()  # Remover qualquer espaço em branco
            if url.startswith('='):
                url = url[1:]  # Remover o sinal de igual se existir
            
            # Remover ponto-e-vírgula do final da URL, se existir
            if url.endswith(';'):
                url = url[:-1]
            
            logger.info(f"Fazendo request para URL: '{url}'")
            
            # Adicionar mais headers para simular um navegador real
            headers_expandidos = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
                "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
                "Cookie": ""  # Deixar vazio para aceitar todos os cookies de sessão
            }
            
            # Técnica mais agressiva: fazer primeiro uma requisição para obter cookies de sessão
            try:
                # Primeira requisição para obter cookies
                session = requests.Session()
                logger.info("Fazendo requisição inicial para obter cookies...")
                initial_response = session.get(url, headers=headers_expandidos, timeout=15)
                
                # Esperar um pouco para simular comportamento humano
                time.sleep(2)
                
                # Verificar se há formulários de login ou aceitação de cookies
                if "login" in initial_response.text.lower() or "cookie" in initial_response.text.lower():
                    logger.info("Detectada possível página de login ou aceitação de cookies")
                
                # Segunda requisição usando a mesma sessão (com cookies)
                logger.info("Fazendo segunda requisição com cookies...")
                response = session.get(url, headers=headers_expandidos, timeout=15)
                
                logger.info(f"Status da resposta: {response.status_code}")
                if response.status_code != 200:
                    logger.error(f"Erro ao acessar o site: Status {response.status_code}")
                    return {}
                
                # Log do tamanho da resposta
                logger.info(f"Tamanho da resposta: {len(response.text)} bytes")
                
                # Verificar se temos conteúdo HTML válido
                if len(response.text) < 1000:
                    logger.warning(f"Resposta muito pequena, pode ser uma página de erro ou redirecionamento: {response.text[:200]}...")
                    return {}
                
                # Usar BeautifulSoup para processar o HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Log dos primeiros 100 caracteres do HTML para diagnóstico
                logger.info(f"Início do HTML: {soup.text[:100]}...")
                
                # Técnicas adicionais de extração
                
                # Método 1: Buscar dados nos scripts JS (onde costumam estar os dados dinâmicos)
                logger.info("Buscando dados em scripts JS...")
                scripts = soup.find_all('script')
                logger.info(f"Encontrados {len(scripts)} blocos de script")
                
                roletas_encontradas = {}
                
                for i, script in enumerate(scripts):
                    script_content = script.string
                    if not script_content:
                        continue
                    
                    # Procurar por padrões de dados de roleta nos scripts
                    # Exemplos: "numbers":["12","7","3",...], "roulette_data":{"numbers":[...]}
                    for pattern in [
                        r'"numbers":\s*\[(.*?)\]',
                        r'"history":\s*\[(.*?)\]',
                        r'"results":\s*\[(.*?)\]',
                        r'"roulette_data":\s*{(.*?)}',
                        r'"table_(\d+)":\s*{(.*?)}'
                    ]:
                        matches = re.findall(pattern, script_content)
                        if matches:
                            logger.info(f"Encontrado padrão {pattern} no script {i+1}")
                            
                            for match_idx, match in enumerate(matches):
                                # Se for uma tupla (com grupos de captura), pegar o segundo elemento
                                if isinstance(match, tuple) and len(match) > 1:
                                    data_str = match[1]
                                else:
                                    data_str = match
                                
                                # Extrair números
                                num_matches = re.findall(r'(\d+)', data_str)
                                if num_matches:
                                    # Limitar para números de roleta (0-36)
                                    numeros = [num for num in num_matches if 0 <= int(num) <= 36][:20]
                                    
                                    if numeros:
                                        table_id = f"roleta-js-{i}-{match_idx}"
                                        table_name = f"Roleta {i+1}-{match_idx+1}"
                                        
                                        roletas_encontradas[table_name] = {
                                            "id": table_id,
                                            "numeros": numeros
                                        }
                                        
                                        logger.info(f"Encontrada roleta via script: {table_name} com números: {numeros[:5]}...")
                
                # Método 2: Busca convencional por elementos HTML
                logger.info("Buscando elementos HTML convencionais...")
                elementos_roleta = soup.select('.roulette-table, .live-roulette, .game-container, [class*="roulette"], [class*="live-casino"], [class*="game-item"], [class*="result"], table, .table')
                
                logger.info(f"Encontrados {len(elementos_roleta)} possíveis elementos de roleta")
                
                for i, elem in enumerate(elementos_roleta):
                    try:
                        # Log para diagnóstico
                        logger.info(f"Analisando elemento {i+1}: classes={elem.get('class', [])}")
                        
                        # Tentar extrair o título da roleta
                        titulo_elem = elem.select_one('.game-title, .table-name, h3, [class*="title"], [class*="name"], caption')
                        titulo = titulo_elem.text.strip() if titulo_elem else f"Roleta HTML {i+1}"
                        
                        # Tentar extrair o ID da roleta
                        id_elem = elem.get('id') or elem.get('data-id') or elem.get('data-table-id')
                        id_roleta = id_elem or f"roleta-html-{i+1}"
                        
                        # Tentar extrair os números recentes
                        numeros_elem = elem.select('.number, .recent-number, .history-number, [class*="number"], [class*="history"], [class*="result"], td, .cell')
                        numeros = []
                        
                        for num_elem in numeros_elem:
                            try:
                                num_text = num_elem.text.strip()
                                # Converter para número (removendo qualquer texto adicional)
                                num_match = re.search(r'\d+', num_text)
                                if num_match:
                                    num = num_match.group()
                                    # Verificar se é um número de roleta válido (0-36)
                                    if 0 <= int(num) <= 36:
                                        numeros.append(num)
                            except Exception as e:
                                logger.error(f"Erro ao extrair número: {str(e)}")
                        
                        # Se encontrou dados válidos, adicionar ao dicionário
                        if numeros:
                            roletas_encontradas[titulo] = {
                                "id": id_roleta,
                                "numeros": numeros
                            }
                            logger.info(f"Encontrada roleta via HTML: {titulo} (ID: {id_roleta}) com {len(numeros)} números")
                        
                    except Exception as e:
                        logger.error(f"Erro ao processar elemento de roleta: {str(e)}")
                
                # Método 3: Buscar iframes que podem conter as roletas
                iframes = soup.find_all('iframe')
                logger.info(f"Encontrados {len(iframes)} iframes que podem conter roletas")
                
                for i, iframe in enumerate(iframes):
                    iframe_src = iframe.get('src')
                    if not iframe_src:
                        continue
                    
                    logger.info(f"Verificando iframe {i+1}: {iframe_src}")
                    
                    try:
                        # Tentar acessar o conteúdo do iframe
                        iframe_response = session.get(iframe_src, headers=headers_expandidos, timeout=10)
                        if iframe_response.status_code == 200:
                            iframe_soup = BeautifulSoup(iframe_response.text, 'html.parser')
                            
                            # Procurar por números no iframe
                            num_elements = iframe_soup.select('[class*="number"], [class*="result"], td')
                            numeros = []
                            
                            for num_elem in num_elements:
                                try:
                                    num_text = num_elem.text.strip()
                                    num_match = re.search(r'\d+', num_text)
                                    if num_match:
                                        num = num_match.group()
                                        if 0 <= int(num) <= 36:
                                            numeros.append(num)
                                except Exception:
                                    pass
                            
                            if numeros:
                                iframe_id = f"roleta-iframe-{i+1}"
                                iframe_name = f"Roleta Iframe {i+1}"
                                
                                roletas_encontradas[iframe_name] = {
                                    "id": iframe_id,
                                    "numeros": numeros
                                }
                                
                                logger.info(f"Encontrada roleta via iframe: {iframe_name} com números: {numeros}")
                    except Exception as e:
                        logger.error(f"Erro ao processar iframe {i+1}: {str(e)}")
                
                return roletas_encontradas
                
            except requests.RequestException as e:
                logger.error(f"Erro na requisição HTTP: {str(e)}")
                return {}
            
        except Exception as e:
            logger.error(f"Erro ao extrair dados da página: {str(e)}")
            return {}
    
    # Loop contínuo para monitoramento em tempo real
    ciclo = 1
    
    while True:
        logger.info(f"Ciclo de verificação HTTP {ciclo}")
        
        # Extrair dados da página
        dados_mesas = extrair_dados_da_pagina()
        
        # Se não conseguiu obter dados, tentar novamente
        if not dados_mesas:
            logger.warning(f"Não foi possível obter dados da página neste ciclo. Tentando novamente em breve.")
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
            # Construir o objeto de dados para inserção/atualização
            dados_para_insert = {
                "titulo": nome_roleta,
                "id_roleta": dados["id"],
                "data_atualizacao": datetime.now().isoformat(),
                "dados": dados
            }
            
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
