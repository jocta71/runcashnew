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

def scrape_roletas_http():
    """Função principal que realiza o scraping das roletas usando HTTP requests e BeautifulSoup"""
    
    logger.info("Iniciando scraper HTTP com requests e BeautifulSoup (compatível com Railway)")
    
    # Dicionário para armazenar dados das roletas e ultimos números vistos
    dados_roletas = {}
    ultimos_numeros = {}
    ciclo = 1
    
    # URLs do cassino a tentar
    urls = [
        "https://es.888casino.com/live-casino/#filters=live-roulette",
        "https://www.888casino.es/live-casino/#filters=live-roulette",
        "https://www.888casino.com/live-casino/#filters=live-roulette",
        "https://www.888casino.pt/live-casino/#filters=live-roulette"
    ]
    
    # Se houver URL personalizada na configuração, adicionar no início da lista
    if CASINO_URL and CASINO_URL not in urls:
        urls.insert(0, CASINO_URL)
    
    # URLs alternativas para APIs diretas (se as páginas normais não funcionarem)
    api_urls = [
        "https://www.888casino.com/website-api/components/videorouletteroomcards/configuration",
        "https://www.888casino.es/website-api/components/videorouletteroomcards/configuration",
        "https://es.888casino.com/website-api/components/videorouletteroomcards/configuration"
    ]
    
    # Criar uma sessão para manter cookies
    session = requests.Session()
    
    # Configurar headers padrão
    headers = {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'TE': 'Trailers'
    }
    
    while True:
        try:
            logger.info(f"Ciclo de verificação {ciclo}")
            
            # Atualizar o User-Agent regularmente
            headers['User-Agent'] = get_random_user_agent()
            session.headers.update(headers)
            
            # Primeiro, tentar as URLs regulares
            html_content = None
            current_url = None
            
            for url in urls:
                try:
                    logger.info(f"Tentando acessar: {url}")
                    response = session.get(url, timeout=30)
                    
                    # Registrar a URL real após possíveis redirecionamentos
                    logger.info(f"URL após redirecionamento: {response.url}")
                    
                    # Aceitar códigos 200 mesmo que a URL tenha mudado ligeiramente
                    if response.status_code == 200 and "888casino" in response.url:
                        logger.info(f"Sucesso ao acessar: {response.url}")
                        html_content = response.text
                        current_url = response.url
                        break
                    else:
                        logger.warning(f"Falha ao acessar {url} - código: {response.status_code}")
                except Exception as e:
                    logger.error(f"Erro ao acessar {url}: {str(e)}")
            
            if html_content:
                # Processar a página HTML
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Procurar elementos de roleta
                roleta_elements = soup.select(".cy-live-casino-grid-item")
                logger.info(f"Encontrados {len(roleta_elements)} elementos de roleta via BeautifulSoup")
                
                if not roleta_elements:
                    logger.warning("Nenhum elemento de roleta encontrado na página normal, tentando extrair do JavaScript")
                    # Tentar extrair dados embutidos no JavaScript
                    scripts = soup.find_all("script")
                    for script in scripts:
                        script_text = script.string if script.string else ""
                        if script_text and "roulette" in script_text.lower():
                            # Procurar por dados JSON
                            json_matches = re.findall(r'window\.__INITIAL_STATE__\s*=\s*({.*?});', script_text, re.DOTALL)
                            if json_matches:
                                try:
                                    json_data = json.loads(json_matches[0])
                                    # Processar os dados JSON para extrair informações da roleta
                                    logger.info("Dados JSON encontrados nos scripts da página")
                                except json.JSONDecodeError:
                                    logger.warning("Erro ao decodificar JSON dos scripts")
                
                # Alternativa: Tentar outros seletores se os padrões conhecidos não funcionarem
                if not roleta_elements:
                    logger.info("Tentando seletores alternativos para elementos de roleta")
                    alternative_selectors = [
                        ".live-casino-grid-item", 
                        ".roulette-item", 
                        ".game-item",
                        ".live-game-item",
                        "[data-game-type='roulette']",
                        ".casino-game-tile"
                    ]
                    
                    for selector in alternative_selectors:
                        alt_elements = soup.select(selector)
                        if alt_elements:
                            logger.info(f"Encontrados {len(alt_elements)} elementos usando seletor alternativo: {selector}")
                            roleta_elements = alt_elements
                            break
                
                # Salvar HTML para depuração se necessário
                if not roleta_elements and ciclo % 10 == 1:  # A cada 10 ciclos
                    try:
                        debug_path = "debug_html.txt"
                        with open(debug_path, "w", encoding="utf-8") as f:
                            f.write(html_content[:5000])  # Salvar os primeiros 5000 caracteres
                        logger.info(f"HTML parcial salvo em {debug_path} para depuração")
                    except Exception as e:
                        logger.error(f"Erro ao salvar HTML para depuração: {str(e)}")
                
                # Processar cada elemento de roleta encontrado
                for i, elemento in enumerate(roleta_elements):
                    try:
                        # Extrair o título da roleta
                        titulo_elem = elemento.select_one(".cy-live-casino-grid-item-title")
                        if not titulo_elem:
                            titulo_elem = elemento.select_one("h3, h4, .title, .game-title")
                            
                        titulo_roleta = titulo_elem.text.strip() if titulo_elem else f"Roleta-{datetime.now().strftime('%H%M%S')}-{i}"
                        
                        logger.info(f"Processando roleta: {titulo_roleta}")
                        
                        # Gerar um ID único para a roleta
                        id_roleta = f"roleta-{hash(titulo_roleta) % 100000}"
                        
                        # Verificar se a roleta está na lista de permitidas
                        if not roleta_permitida_por_id(id_roleta):
                            logger.info(f"Roleta {titulo_roleta} não está na lista de permitidas. Pulando.")
                            continue
                        
                        # Extrair números da roleta
                        numeros_spans = elemento.select(".cy-live-casino-grid-item-infobar-draws span, .cy-live-casino-grid-item-infobar-draws div")
                        numeros_atuais = []
                        
                        for span in numeros_spans:
                            texto = span.text.strip()
                            if texto and texto.isdigit():
                                numeros_atuais.append(texto)
                        
                        # Se não encontrou números nos spans, tentar extrair do texto completo
                        if not numeros_atuais:
                            infobar = elemento.select_one(".cy-live-casino-grid-item-infobar-draws, .infobar, .draws, .results, .game-results")
                            if infobar:
                                texto_completo = infobar.text.strip()
                                matches = re.findall(r'\d+', texto_completo)
                                numeros_atuais = matches
                        
                        # Tentar outros seletores comuns
                        if not numeros_atuais:
                            for selector in ['.number', '.roulette-number', '.result', '[data-result]', '[data-number]', '.history', '.previous-numbers']:
                                elementos_numero = elemento.select(selector)
                                for elem in elementos_numero:
                                    texto = elem.text.strip()
                                    if texto and texto.isdigit():
                                        numeros_atuais.append(texto)
                        
                        logger.info(f"Números extraídos para {titulo_roleta}: {numeros_atuais}")
                        
                        if numeros_atuais:
                            # O primeiro número é o mais recente
                            ultimo_numero = numeros_atuais[0]
                            
                            # Verificar se é um número novo
                            numero_anterior = ultimos_numeros.get(titulo_roleta)
                            
                            if not numero_anterior or ultimo_numero != numero_anterior:
                                logger.info(f"NOVO NÚMERO para {titulo_roleta}: {ultimo_numero} (anterior: {numero_anterior})")
                                
                                # Atualizar o último número visto
                                ultimos_numeros[titulo_roleta] = ultimo_numero
                                
                                # Criar analisador para mesa se não existir
                                if titulo_roleta not in analisadores_mesas:
                                    analisadores_mesas[titulo_roleta] = StrategyAnalyzer(titulo_roleta)
                                    logger.info(f"Novo analisador criado para mesa: {titulo_roleta}")
                                
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
                        logger.error(f"Erro ao processar roleta {i}: {str(e)}")
            
            else:
                # Se não conseguiu acessar as páginas normais, tentar APIs diretas
                logger.info("Tentando acessar as APIs diretas")
                
                for api_url in api_urls:
                    try:
                        # Adicionar headers específicos para requisições de API
                        api_headers = headers.copy()
                        api_headers.update({
                            'Accept': 'application/json',
                            'Content-Type': 'application/json',
                            'X-Requested-With': 'XMLHttpRequest'
                        })
                        
                        response = session.get(api_url, headers=api_headers, timeout=30)
                        
                        if response.status_code == 200:
                            logger.info(f"Sucesso ao acessar API: {api_url}")
                            try:
                                # Tentar extrair dados JSON da API
                                json_data = response.json()
                                
                                # Processar os dados da API - será específico para cada API
                                if 'data' in json_data and 'rouletteTables' in json_data.get('data', {}):
                                    logger.info("Dados de roleta encontrados na API")
                                    roulette_tables = json_data['data']['rouletteTables']
                                    
                                    # Processar cada roleta recebida da API
                                    for table in roulette_tables:
                                        try:
                                            table_name = table.get('name', f"Roleta-API-{datetime.now().strftime('%H%M%S')}")
                                            logger.info(f"Processando roleta da API: {table_name}")
                                            
                                            # Criar ID para a roleta
                                            id_roleta = f"roleta-{hash(table_name) % 100000}"
                                            
                                            # Verificar se está na lista de permitidas
                                            if not roleta_permitida_por_id(id_roleta):
                                                logger.info(f"Roleta {table_name} da API não está na lista de permitidas. Pulando.")
                                                continue
                                            
                                            # Extrair números (específico para o formato de API do 888casino)
                                            recent_results = table.get('recentResults', [])
                                            if recent_results:
                                                numeros_atuais = [str(num) for num in recent_results]
                                                
                                                logger.info(f"Números extraídos da API para {table_name}: {numeros_atuais}")
                                                
                                                if numeros_atuais:
                                                    # Processar os números como nas roletas normais
                                                    ultimo_numero = numeros_atuais[0]
                                                    numero_anterior = ultimos_numeros.get(table_name)
                                                    
                                                    if not numero_anterior or ultimo_numero != numero_anterior:
                                                        logger.info(f"NOVO NÚMERO (API) para {table_name}: {ultimo_numero}")
                                                        
                                                        # Processar o número como nas roletas normais
                                                        ultimos_numeros[table_name] = ultimo_numero
                                                        
                                                        if table_name not in analisadores_mesas:
                                                            analisadores_mesas[table_name] = StrategyAnalyzer(table_name)
                                                        
                                                        if analisadores_mesas[table_name].add_numbers([ultimo_numero]):
                                                            logger.info(f"Novo número adicionado para {table_name}: {ultimo_numero}")
                                                        
                                                        if table_name not in dados_roletas:
                                                            dados_roletas[table_name] = {
                                                                "numeros": [],
                                                                "ultima_atualizacao": "",
                                                                "id": id_roleta
                                                            }
                                                        
                                                        dados_roletas[table_name]["numeros"] = numeros_atuais + [
                                                            n for n in dados_roletas[table_name].get("numeros", [])
                                                            if n not in numeros_atuais
                                                        ]
                                                        
                                                        dados_roletas[table_name]["numeros"] = dados_roletas[table_name]["numeros"][:20]
                                                        
                                                        dados_roletas[table_name].update({
                                                            "ultima_atualizacao": datetime.now().isoformat(),
                                                            "estrategia": analisadores_mesas[table_name].get_data()
                                                        })
                                                        
                                                        update_data = {table_name: dados_roletas[table_name]}
                                                        atualizar_supabase(update_data)
                                        except Exception as e:
                                            logger.error(f"Erro ao processar roleta da API: {str(e)}")
                                else:
                                    logger.warning("Estrutura de API desconhecida")
                                    # Salvando a resposta para análise
                                    try:
                                        with open("api_response.json", "w") as f:
                                            json.dump(json_data, f, indent=2)
                                        logger.info("Resposta da API salva em api_response.json para análise")
                                    except Exception as e:
                                        logger.error(f"Erro ao salvar resposta da API: {str(e)}")
                            except Exception as e:
                                logger.error(f"Erro ao processar dados da API: {str(e)}")
                            
                            break
                        else:
                            logger.warning(f"Falha ao acessar API {api_url} - código: {response.status_code}")
                    except Exception as e:
                        logger.error(f"Erro ao acessar API {api_url}: {str(e)}")
            
            # Incrementar contador de ciclos
            ciclo += 1
            
            # Pausa entre verificações
            time.sleep(VERIFICACAO_INTERVALO)
            
            # Reiniciar a sessão periodicamente para evitar problemas
            if ciclo % 30 == 0:
                logger.info("Reiniciando sessão HTTP")
                session = requests.Session()
                session.headers.update(headers)
        
        except Exception as e:
            logger.error(f"Erro crítico no scraper: {str(e)}")
            # Pequena pausa para não sobrecarregar em caso de erros repetidos
            time.sleep(10)

def scrape_api_apenas():
    """Função alternativa que usa requests e BeautifulSoup para todas as plataformas"""
    logger.info("Usando scraper HTTP para todas as plataformas")
    scrape_roletas_http()

def scrape_roletas():
    """Função principal - redireciona para a implementação HTTP"""
    scrape_roletas_http()

if __name__ == "__main__":
    try:
        logger.info("Iniciando scraper em modo contínuo")
        scrape_roletas_http()
    except KeyboardInterrupt:
        logger.info("Scraper interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao executar scraper: {str(e)}")
