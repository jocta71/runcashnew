import time
import random
import re
import json
import os
import platform
from datetime import datetime
import logging
import requests
import asyncio
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
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

def scrape_roletas_playwright():
    """Função principal que realiza o scraping das roletas usando Playwright"""
    
    logger.info("Iniciando scraper com Playwright (compatível com Railway)")
    
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
    
    with sync_playwright() as p:
        try:
            # Iniciar um navegador Chromium
            browser = p.chromium.launch()
            
            # Loop principal
            while True:
                logger.info(f"Ciclo de verificação {ciclo}")
                
                # Criar um novo contexto para este ciclo (para evitar problemas com cookies/cache)
                context = browser.new_context(
                    user_agent=get_random_user_agent(),
                    viewport={"width": 1920, "height": 1080}
                )
                page = context.new_page()
                
                # Tentar acessar uma das URLs
                for url in urls:
                    try:
                        logger.info(f"Tentando acessar: {url}")
                        response = page.goto(url, wait_until="networkidle", timeout=60000)
                        
                        if response and response.ok and "888casino" in page.url and "live-casino" in page.url:
                            logger.info(f"Sucesso ao acessar: {url}")
                            break
                        else:
                            logger.warning(f"Falha ao acessar {url} - código: {response.status if response else 'N/A'}")
                    except Exception as e:
                        logger.error(f"Erro ao acessar {url}: {str(e)}")
                
                # Procurar elementos de roleta
                logger.info("Buscando elementos de roleta...")
                try:
                    # Aguardar algum tempo para a página carregar completamente
                    page.wait_for_timeout(5000)
                    
                    # Verificar os elementos de roleta no DOM
                    roleta_elements = page.query_selector_all(".cy-live-casino-grid-item")
                    
                    logger.info(f"Encontrados {len(roleta_elements)} elementos de roleta")
                    
                    # Processar cada elemento de roleta
                    for i, elemento in enumerate(roleta_elements):
                        try:
                            # Extrair o título da roleta
                            titulo_elem = elemento.query_selector(".cy-live-casino-grid-item-title")
                            titulo_roleta = titulo_elem.inner_text() if titulo_elem else f"Roleta-{datetime.now().strftime('%H%M%S')}-{i}"
                            
                            logger.info(f"Processando roleta: {titulo_roleta}")
                            
                            # Gerar um ID único para a roleta
                            id_roleta = f"roleta-{hash(titulo_roleta) % 100000}"
                            
                            # Verificar se a roleta está na lista de permitidas
                            if not roleta_permitida_por_id(id_roleta):
                                logger.info(f"Roleta {titulo_roleta} não está na lista de permitidas. Pulando.")
                                continue
                            
                            # Extrair números usando JavaScript
                            numeros_js = page.evaluate("""(elemento) => {
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
                                    
                                    // Remover duplicatas
                                    return [...new Set(numeros)];
                                } catch (error) {
                                    console.error('Erro ao extrair números:', error);
                                    return [];
                                }
                            }""", elemento)
                            
                            # Converter para strings
                            numeros_atuais = [str(num) for num in numeros_js]
                            
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
                
                except Exception as e:
                    logger.error(f"Erro ao buscar elementos: {str(e)}")
                
                # Fechar o contexto para limpar cookies e cache
                context.close()
                
                # Incrementar contador de ciclos
                ciclo += 1
                
                # Pequena pausa entre ciclos
                time.sleep(VERIFICACAO_INTERVALO)
                
                # Verificar periodicamente se o navegador ainda está respondendo
                if ciclo % 30 == 0:
                    logger.info("Verificando conexão do navegador...")
                    try:
                        # Testar se o navegador ainda está funcionando
                        test_context = browser.new_context()
                        test_page = test_context.new_page()
                        test_page.goto("about:blank")
                        test_context.close()
                        logger.info("Navegador OK.")
                    except Exception as e:
                        logger.error(f"Erro no navegador: {str(e)}")
                        # Reiniciar o navegador
                        browser.close()
                        browser = p.chromium.launch()
                        logger.info("Navegador reiniciado.")
        
        except Exception as e:
            logger.error(f"Erro crítico no scraper: {str(e)}")
        
        finally:
            # Certificar-se de fechar o navegador
            try:
                browser.close()
            except:
                pass

def scrape_api_apenas():
    """Função alternativa que usa Playwright para todas as plataformas"""
    logger.info("Usando scraper com Playwright para todas as plataformas")
    scrape_roletas_playwright()

def scrape_roletas():
    """Função principal - redireciona para a implementação Playwright"""
    scrape_roletas_playwright()

if __name__ == "__main__":
    try:
        logger.info("Iniciando scraper em modo contínuo")
        scrape_roletas_playwright()
    except KeyboardInterrupt:
        logger.info("Scraper interrompido pelo usuário")
    except Exception as e:
        logger.error(f"Erro ao executar scraper: {str(e)}")
