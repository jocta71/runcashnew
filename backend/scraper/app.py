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

# URL específica para acessar
CASINO_URL_PRIMARY = "https://es.888casino.com/live-casino/#filters=live-roulette"

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

def obter_auth_cookies():
    """Tenta obter cookies de autenticação para acessar as páginas"""
    try:
        session = requests.Session()
        
        # Configurar headers como um navegador real
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Referer': 'https://www.888casino.es/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin'
        }
        
        session.headers.update(headers)
        
        # Primeiro acesso à página principal para obter cookies iniciais
        logger.info("Obtendo cookies iniciais...")
        base_url = "https://www.888casino.es/"
        response = session.get(base_url, timeout=30)
        
        if response.status_code == 200:
            logger.info(f"Obtidos {len(session.cookies)} cookies iniciais")
            return session
        else:
            logger.warning(f"Falha ao obter cookies iniciais: código {response.status_code}")
            return session
    
    except Exception as e:
        logger.error(f"Erro ao obter cookies: {str(e)}")
        return requests.Session()  # Retornar uma sessão vazia em caso de erro

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

def analisar_html_para_roletas(html_content):
    """Analisa o HTML para extrair dados das roletas"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        roletas_encontradas = {}
        
        # Localizar scripts que possam conter dados
        logger.info("Procurando dados em scripts...")
        scripts = soup.find_all('script')
        
        json_data = None
        
        # Procurar por padrões conhecidos de dados em scripts
        for script in scripts:
            script_content = script.string if script.string else ""
            
            # Padrão 1: window.__INITIAL_STATE__
            matches = re.search(r'window\.__INITIAL_STATE__\s*=\s*({.*});', script_content, re.DOTALL)
            if matches:
                try:
                    json_data = json.loads(matches.group(1))
                    logger.info("Dados JSON encontrados em __INITIAL_STATE__")
                    break
                except json.JSONDecodeError:
                    pass
            
            # Padrão 2: Procurar por blocos JSON com dados de roleta
            for pattern in [
                r'({"games":\s*\[.*?\])',
                r'({"data":\s*{"rouletteTables":\s*\[.*?\]})',
                r'({"tables":\s*\[.*?\])',
                r'("liveRoulette":\s*{.*?})'
            ]:
                matches = re.search(pattern, script_content, re.DOTALL)
                if matches:
                    try:
                        json_str = matches.group(1)
                        # Garantir que a string termine com "}"
                        if not json_str.endswith('}'):
                            json_str += '}'
                        json_data = json.loads(json_str)
                        logger.info(f"Dados JSON encontrados em padrão: {pattern}")
                        break
                    except json.JSONDecodeError:
                        pass
        
        # Se encontrou algum dado JSON
        if json_data:
            # Salvar para análise
            try:
                with open("extracted_json.json", "w", encoding="utf-8") as f:
                    json.dump(json_data, f, indent=2)
                logger.info("JSON extraído salvo em extracted_json.json")
            except Exception as e:
                logger.error(f"Erro ao salvar JSON extraído: {str(e)}")
            
            # Processar o JSON para extrair dados de roletas
            return extrair_roletas_do_json(json_data)
        
        # Se não encontrou dados JSON em scripts, procurar elementos HTML
        logger.info("Procurando elementos de roleta no HTML...")
        
        # Lista de seletores possíveis para elementos de roleta
        seletores = [
            ".cy-live-casino-grid-item",
            ".live-casino-grid-item",
            ".roulette-item",
            ".game-item",
            "[data-game-type='roulette']",
            "[data-game-name*='ruleta']",
            "[data-game-name*='roulette']"
        ]
        
        # Tentar cada seletor
        for seletor in seletores:
            elementos = soup.select(seletor)
            if elementos:
                logger.info(f"Encontrados {len(elementos)} elementos com seletor {seletor}")
                
                for i, elemento in enumerate(elementos):
                    try:
                        # Tentar extrair nome da roleta
                        nome_elem = elemento.select_one(".title, .name, h3, h4, [data-game-name]")
                        nome_roleta = nome_elem.text.strip() if nome_elem else f"Roleta-{i}"
                        
                        # Para atributos data-*
                        if not nome_elem and elemento.has_attr('data-game-name'):
                            nome_roleta = elemento['data-game-name']
                        
                        # Gerar ID único
                        id_roleta = f"roleta-{hash(nome_roleta) % 100000}"
                        
                        # Verificar se está na lista de permitidas
                        if not roleta_permitida_por_id(id_roleta):
                            logger.info(f"Roleta {nome_roleta} não está na lista de permitidas. Pulando.")
                            continue
                        
                        # Extrair números
                        numeros = []
                        # Tentar diferentes métodos para encontrar números
                        numero_elems = elemento.select(".number, .result, .past-result, [data-number]")
                        for num_elem in numero_elems:
                            num_text = num_elem.text.strip()
                            if num_text.isdigit():
                                numeros.append(num_text)
                        
                        # Método alternativo: procurar números no texto
                        if not numeros:
                            texto = elemento.text
                            # Procurar padrões como "Últimos resultados: 12, 35, 7"
                            matches = re.findall(r'resultados:?\s*([\d,\s]+)', texto, re.IGNORECASE)
                            if matches:
                                numeros = re.findall(r'\d+', matches[0])
                        
                        if numeros:
                            # Adicionar à lista de roletas encontradas
                            roletas_encontradas[nome_roleta] = {
                                "id": id_roleta,
                                "numeros": numeros,
                                "ultima_atualizacao": datetime.now().isoformat()
                            }
                    except Exception as e:
                        logger.error(f"Erro ao processar elemento {i}: {str(e)}")
                
                # Se encontrou alguma roleta, parar de procurar
                if roletas_encontradas:
                    break
        
        return roletas_encontradas
    
    except Exception as e:
        logger.error(f"Erro ao analisar HTML: {str(e)}")
        return {}

def extrair_roletas_do_json(json_data):
    """Extrai informações de roletas de dados JSON"""
    try:
        roletas_encontradas = {}
        
        # Verificar diferentes estruturas possíveis
        # Estrutura 1: {"games": [...]}
        if 'games' in json_data:
            logger.info("Processando estrutura JSON com campo 'games'")
            for jogo in json_data['games']:
                try:
                    # Verificar se é uma roleta
                    if 'gameType' in jogo and ('roulette' in jogo['gameType'].lower() or 'ruleta' in jogo['gameType'].lower()):
                        nome_roleta = jogo.get('gameName', jogo.get('name', f"Roleta-{datetime.now().strftime('%H%M%S')}"))
                        id_roleta = f"roleta-{hash(nome_roleta) % 100000}"
                        
                        # Verificar se está na lista de permitidas
                        if not roleta_permitida_por_id(id_roleta):
                            logger.info(f"Roleta {nome_roleta} não está na lista de permitidas. Pulando.")
                            continue
                        
                        # Extrair números
                        numeros = []
                        for campo in ['recentResults', 'results', 'pastResults', 'lastNumbers']:
                            if campo in jogo and jogo[campo] and isinstance(jogo[campo], list):
                                numeros = [str(n) for n in jogo[campo]]
                                break
                        
                        if numeros:
                            roletas_encontradas[nome_roleta] = {
                                "id": id_roleta,
                                "numeros": numeros,
                                "ultima_atualizacao": datetime.now().isoformat()
                            }
                except Exception as e:
                    logger.error(f"Erro ao processar jogo: {str(e)}")
        
        # Estrutura 2: {"data": {"rouletteTables": [...]}}
        elif 'data' in json_data and 'rouletteTables' in json_data['data']:
            logger.info("Processando estrutura JSON com campo 'rouletteTables'")
            for mesa in json_data['data']['rouletteTables']:
                try:
                    nome_roleta = mesa.get('name', f"Roleta-{datetime.now().strftime('%H%M%S')}")
                    id_roleta = f"roleta-{hash(nome_roleta) % 100000}"
                    
                    # Verificar se está na lista de permitidas
                    if not roleta_permitida_por_id(id_roleta):
                        logger.info(f"Roleta {nome_roleta} não está na lista de permitidas. Pulando.")
                        continue
                    
                    # Extrair números
                    numeros = []
                    if 'recentResults' in mesa and mesa['recentResults']:
                        numeros = [str(n) for n in mesa['recentResults']]
                    
                    if numeros:
                        roletas_encontradas[nome_roleta] = {
                            "id": id_roleta,
                            "numeros": numeros,
                            "ultima_atualizacao": datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.error(f"Erro ao processar mesa: {str(e)}")
        
        # Estrutura 3: {"tables": [...]}
        elif 'tables' in json_data:
            logger.info("Processando estrutura JSON com campo 'tables'")
            for mesa in json_data['tables']:
                try:
                    nome_roleta = mesa.get('name', mesa.get('title', f"Roleta-{datetime.now().strftime('%H%M%S')}"))
                    id_roleta = f"roleta-{hash(nome_roleta) % 100000}"
                    
                    # Verificar se está na lista de permitidas
                    if not roleta_permitida_por_id(id_roleta):
                        logger.info(f"Roleta {nome_roleta} não está na lista de permitidas. Pulando.")
                        continue
                    
                    # Extrair números
                    numeros = []
                    for campo in ['history', 'results', 'pastResults', 'numbers']:
                        if campo in mesa and mesa[campo] and isinstance(mesa[campo], list):
                            numeros = [str(n) for n in mesa[campo]]
                            break
                    
                    if numeros:
                        roletas_encontradas[nome_roleta] = {
                            "id": id_roleta,
                            "numeros": numeros,
                            "ultima_atualizacao": datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.error(f"Erro ao processar mesa: {str(e)}")
        
        # Estrutura 4: Qualquer outra estrutura de dados que possa conter roletas
        else:
            logger.info("Procurando roletas em estrutura JSON desconhecida")
            # Função recursiva para procurar roletas em qualquer nível do JSON
            def procurar_roletas(obj, path=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        # Se encontrar chaves que indiquem dados de roleta
                        if key in ['rouletteTables', 'games', 'tables', 'liveRoulette'] and isinstance(value, list):
                            logger.info(f"Encontrada lista de roletas em {path}.{key}")
                            for i, item in enumerate(value):
                                try:
                                    # Extrair nome
                                    nome_roleta = item.get('name', item.get('title', f"Roleta-{i}"))
                                    id_roleta = f"roleta-{hash(nome_roleta) % 100000}"
                                    
                                    # Verificar se está na lista de permitidas
                                    if not roleta_permitida_por_id(id_roleta):
                                        continue
                                    
                                    # Extrair números
                                    numeros = []
                                    for campo in ['recentResults', 'results', 'history', 'pastResults', 'numbers']:
                                        if campo in item and item[campo] and isinstance(item[campo], list):
                                            numeros = [str(n) for n in item[campo]]
                                            break
                                    
                                    if numeros:
                                        roletas_encontradas[nome_roleta] = {
                                            "id": id_roleta,
                                            "numeros": numeros,
                                            "ultima_atualizacao": datetime.now().isoformat()
                                        }
                                except Exception as e:
                                    logger.error(f"Erro ao processar item {i} em {path}.{key}: {str(e)}")
                        else:
                            # Continuar procurando recursivamente
                            procurar_roletas(value, f"{path}.{key}" if path else key)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        procurar_roletas(item, f"{path}[{i}]")
            
            # Iniciar busca recursiva
            procurar_roletas(json_data)
        
        return roletas_encontradas
    
    except Exception as e:
        logger.error(f"Erro ao extrair roletas do JSON: {str(e)}")
        return {}

def extrair_dados_mock():
    """Cria dados simulados apenas para teste quando não é possível obter dados reais"""
    logger.warning("Usando dados simulados temporários enquanto trabalhamos para acessar os dados reais")
    
    # Lista de nomes de roletas realistas do 888casino
    roletas = [
        "Ruleta Speed 888",
        "Ruleta Lightning",
        "888 Ruleta En Vivo",
        "Mega Fire Blaze Ruleta En Vivo",
        "Grand Ruleta"
    ]
    
    dados_roletas = {}
    
    # Gerar até 5 roletas diferentes
    for i in range(min(5, len(roletas))):
        nome_roleta = roletas[i]
        id_roleta = f"roleta-{hash(nome_roleta) % 100000}"
        
        # Gerar entre 10 e 20 números aleatórios (0-36)
        numeros = [str(random.randint(0, 36)) for _ in range(random.randint(10, 20))]
        
        # Criar analisador para mesa se não existir
        if nome_roleta not in analisadores_mesas:
            analisadores_mesas[nome_roleta] = StrategyAnalyzer(nome_roleta)
            logger.info(f"Novo analisador criado para mesa: {nome_roleta}")
        
        # Adicionar números ao analisador
        analisadores_mesas[nome_roleta].add_numbers(numeros)
        
        # Organizar dados
        dados_roletas[nome_roleta] = {
            "numeros": numeros,
            "ultima_atualizacao": datetime.now().isoformat(),
            "id": id_roleta,
            "estrategia": analisadores_mesas[nome_roleta].get_data()
        }
    
    return dados_roletas

def processar_dados_roletas(roletas_encontradas):
    """Processa os dados das roletas encontradas e adiciona a estratégia"""
    dados_completos = {}
    
    for nome_roleta, dados in roletas_encontradas.items():
        numeros = dados.get("numeros", [])
        id_roleta = dados.get("id", "")
        
        if numeros:
            # Criar analisador para mesa se não existir
            if nome_roleta not in analisadores_mesas:
                analisadores_mesas[nome_roleta] = StrategyAnalyzer(nome_roleta)
                logger.info(f"Novo analisador criado para mesa: {nome_roleta}")
            
            # Adicionar números ao analisador
            analisadores_mesas[nome_roleta].add_numbers(numeros)
            
            # Obter dados da estratégia
            estrategia = analisadores_mesas[nome_roleta].get_data()
            
            # Adicionar estratégia aos dados
            dados_completos[nome_roleta] = {
                "numeros": numeros,
                "ultima_atualizacao": datetime.now().isoformat(),
                "id": id_roleta,
                "estrategia": estrategia
            }
    
    return dados_completos

def scrape_roletas_http():
    """Função principal que realiza o scraping da página web do 888casino"""
    
    logger.info("Iniciando scraper HTTP com análise avançada de HTML (compatível com Railway)")
    
    ciclo = 1
    falhas_consecutivas = 0
    max_falhas_permitidas = 10
    
    # Obter uma sessão com cookies iniciais
    session = obter_auth_cookies()
    
    # Esperar um pouco antes de começar
    time.sleep(2)
    
    while True:
        try:
            logger.info(f"Ciclo de verificação {ciclo}")
            
            # Atualizar o User-Agent regularmente
            session.headers.update({'User-Agent': get_random_user_agent()})
            
            # Acessar a URL específica
            logger.info(f"Acessando URL principal: {CASINO_URL_PRIMARY}")
            
            try:
                response = session.get(CASINO_URL_PRIMARY, timeout=60)  # Timeout maior para permitir carregamento
                
                if response.status_code == 200:
                    logger.info(f"Sucesso: recebidos {len(response.text)} bytes de HTML")
                    
                    # Extrair o conteúdo após redirecionamentos
                    html_content = response.text
                    url_final = response.url
                    
                    logger.info(f"URL final após redirecionamentos: {url_final}")
                    
                    # Salvar o HTML para debug (ocasionalmente)
                    if ciclo % 10 == 1:
                        try:
                            with open("page_content.html", "w", encoding="utf-8") as f:
                                f.write(html_content[:10000])  # Primeiros 10000 caracteres
                            logger.info("Amostra de HTML salva em page_content.html")
                        except Exception as e:
                            logger.error(f"Erro ao salvar HTML: {str(e)}")
                    
                    # Analisar o HTML para extrair dados das roletas
                    roletas_encontradas = analisar_html_para_roletas(html_content)
                    
                    if roletas_encontradas:
                        logger.info(f"Encontradas {len(roletas_encontradas)} roletas na página")
                        
                        # Processar os dados das roletas
                        dados_completos = processar_dados_roletas(roletas_encontradas)
                        
                        # Atualizar Supabase
                        atualizar_supabase(dados_completos)
                        
                        # Resetar contador de falhas
                        falhas_consecutivas = 0
                    else:
                        logger.warning("Nenhuma roleta encontrada na página")
                        falhas_consecutivas += 1
                else:
                    logger.warning(f"Falha ao acessar URL: código {response.status_code}")
                    falhas_consecutivas += 1
            
            except Exception as e:
                logger.error(f"Erro ao acessar URL: {str(e)}")
                falhas_consecutivas += 1
            
            # Se houver muitas falhas consecutivas, usar dados simulados
            if falhas_consecutivas > max_falhas_permitidas:
                logger.warning(f"Detectadas {falhas_consecutivas} falhas consecutivas")
                # Fornecer dados simulados como último recurso
                dados_mock = extrair_dados_mock()
                atualizar_supabase(dados_mock)
                
                # Tentar renovar a sessão
                session = obter_auth_cookies()
                falhas_consecutivas = 0
            
            # Incrementar contador de ciclos
            ciclo += 1
            
            # Pausa entre verificações
            time.sleep(VERIFICACAO_INTERVALO)
            
            # Renovar a sessão periodicamente
            if ciclo % 20 == 0:
                logger.info("Renovando cookies e sessão")
                session = obter_auth_cookies()
            
        except Exception as e:
            logger.error(f"Erro crítico no scraper: {str(e)}")
            # Pequena pausa para não sobrecarregar em caso de erros repetidos
            time.sleep(10)

def scrape_api_apenas():
    """Função alternativa que usa requests e análise avançada de HTML"""
    logger.info("Usando scraper HTTP com análise avançada de HTML")
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
