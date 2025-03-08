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

def acessar_api_direta():
    """Função para acessar diretamente a API do 888casino e extrair dados das roletas"""
    try:
        # Criar uma sessão para manter cookies
        session = requests.Session()
        
        # Configurar headers para simular um navegador
        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        session.headers.update(headers)
        
        # URLs de API a tentar
        api_urls = [
            "https://www.888casino.es/website-api/gamelist/getliverouletteregulargames/",
            "https://www.888casino.es/website-api/components/livecasinorollingstatus/configuration",
            "https://www.888casino.com/website-api/gamelist/getliverouletteregulargames/",
            "https://es.888casino.com/website-api/gamelist/getliverouletteregulargames/"
        ]
        
        # Tentar cada URL da API
        for api_url in api_urls:
            try:
                logger.info(f"Tentando acessar API: {api_url}")
                response = session.get(api_url, timeout=30)
                
                if response.status_code == 200:
                    logger.info(f"Sucesso ao acessar API: {api_url} - código: {response.status_code}")
                    
                    try:
                        json_data = response.json()
                        
                        # Se a API retornar dados, processar e retornar
                        if json_data:
                            logger.info(f"Dados JSON recebidos da API: {api_url}")
                            # Salvar a resposta completa para análise futura
                            try:
                                with open("api_response.json", "w") as f:
                                    json.dump(json_data, f, indent=2)
                                logger.info("Resposta da API salva em api_response.json para análise")
                            except Exception as e:
                                logger.error(f"Erro ao salvar resposta da API: {str(e)}")
                            
                            return json_data
                    except Exception as e:
                        logger.error(f"Erro ao processar resposta da API {api_url}: {str(e)}")
                else:
                    logger.warning(f"Falha ao acessar API {api_url} - código: {response.status_code}")
            except Exception as e:
                logger.error(f"Erro ao acessar API {api_url}: {str(e)}")
        
        return None
    except Exception as e:
        logger.error(f"Erro ao acessar APIs diretas: {str(e)}")
        return None

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

def processar_json_api(json_data):
    """Processa dados JSON da API do 888casino para extrair informações das roletas"""
    try:
        dados_roletas = {}
        
        # Verificar várias estruturas de dados possíveis
        if 'games' in json_data:
            # Estrutura 1: {"games": [...]}
            logger.info("Processando estrutura de API com campo 'games'")
            jogos = json_data['games']
            
            for jogo in jogos:
                if 'gameType' in jogo and 'roulette' in jogo['gameType'].lower():
                    try:
                        nome_roleta = jogo.get('gameName', f"Roleta-{datetime.now().strftime('%H%M%S')}")
                        id_roleta = f"roleta-{hash(nome_roleta) % 100000}"
                        
                        # Verificar se a roleta está na lista de permitidas
                        if not roleta_permitida_por_id(id_roleta):
                            logger.info(f"Roleta {nome_roleta} não está na lista de permitidas. Pulando.")
                            continue
                        
                        # Extrair números se disponíveis
                        numeros = []
                        if 'recentResults' in jogo:
                            numeros = [str(n) for n in jogo['recentResults']]
                        elif 'results' in jogo:
                            numeros = [str(n) for n in jogo['results']]
                        
                        if numeros:
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
                            
                            logger.info(f"Dados extraídos para roleta {nome_roleta}: {numeros}")
                    except Exception as e:
                        logger.error(f"Erro ao processar jogo da API: {str(e)}")
        
        elif 'rouletteTables' in json_data.get('data', {}):
            # Estrutura 2: {"data": {"rouletteTables": [...]}}
            logger.info("Processando estrutura de API com campo 'rouletteTables'")
            mesas = json_data['data']['rouletteTables']
            
            for mesa in mesas:
                try:
                    nome_roleta = mesa.get('name', f"Roleta-{datetime.now().strftime('%H%M%S')}")
                    id_roleta = f"roleta-{hash(nome_roleta) % 100000}"
                    
                    # Verificar se a roleta está na lista de permitidas
                    if not roleta_permitida_por_id(id_roleta):
                        logger.info(f"Roleta {nome_roleta} não está na lista de permitidas. Pulando.")
                        continue
                    
                    # Extrair números
                    numeros = []
                    if 'recentResults' in mesa:
                        numeros = [str(n) for n in mesa['recentResults']]
                    
                    if numeros:
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
                        
                        logger.info(f"Dados extraídos para roleta {nome_roleta}: {numeros}")
                except Exception as e:
                    logger.error(f"Erro ao processar mesa da API: {str(e)}")
        
        # Se não encontrou dados em nenhuma estrutura conhecida
        if not dados_roletas:
            logger.warning("Formato de API desconhecido - nenhum dado extraído")
            return None
        
        return dados_roletas
    except Exception as e:
        logger.error(f"Erro ao processar JSON da API: {str(e)}")
        return None

def scrape_roletas_http():
    """Função principal que realiza o scraping das roletas usando acesso direto a APIs"""
    
    logger.info("Iniciando scraper HTTP com requests (compatível com Railway)")
    
    ciclo = 1
    falhas_consecutivas = 0
    max_falhas_permitidas = 10
    
    while True:
        try:
            logger.info(f"Ciclo de verificação {ciclo}")
            
            # Tentar acessar diretamente as APIs
            json_data = acessar_api_direta()
            
            if json_data:
                # Processar os dados da API
                dados_roletas = processar_json_api(json_data)
                
                if dados_roletas:
                    logger.info(f"Dados extraídos com sucesso para {len(dados_roletas)} roletas")
                    # Atualizar Supabase com os dados extraídos
                    atualizar_supabase(dados_roletas)
                    # Resetar contador de falhas em caso de sucesso
                    falhas_consecutivas = 0
                else:
                    logger.warning("Não foi possível extrair dados das APIs")
                    falhas_consecutivas += 1
            else:
                # Nenhum dado da API, usar dados simulados temporários para teste
                logger.warning("Nenhum dado obtido das APIs")
                falhas_consecutivas += 1
                
                # Se houver muitas falhas consecutivas, usar dados simulados
                if falhas_consecutivas > max_falhas_permitidas:
                    logger.warning(f"Detectadas {falhas_consecutivas} falhas consecutivas")
                    # Fornecer dados simulados como último recurso
                    dados_mock = extrair_dados_mock()
                    atualizar_supabase(dados_mock)
            
            # Incrementar contador de ciclos
            ciclo += 1
            
            # Pausa entre verificações
            time.sleep(VERIFICACAO_INTERVALO)
            
        except Exception as e:
            logger.error(f"Erro crítico no scraper: {str(e)}")
            # Pequena pausa para não sobrecarregar em caso de erros repetidos
            time.sleep(10)

def scrape_api_apenas():
    """Função alternativa que usa requests e acesso direto a APIs"""
    logger.info("Usando scraper HTTP com acesso direto a APIs")
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
