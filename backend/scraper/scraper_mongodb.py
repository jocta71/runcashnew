#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Scraper roletas MongoDB - Versão Minimalista
"""

import time
import random
import re
import os
import logging
import hashlib
from datetime import datetime
import threading
import queue
import sys

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

from config import CASINO_URL, roleta_permitida_por_id, MAX_CICLOS, MAX_ERROS_CONSECUTIVOS
from event_manager import event_manager

# Configurar logging minimalista - apenas erros críticos
logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger('runcash')
logger.setLevel(logging.CRITICAL)

# Remover todos os handlers existentes
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Variáveis de controle
ultima_atividade = time.time()
erros_consecutivos = 0
driver_global = None

# Ambiente
IS_PRODUCTION = os.environ.get('PRODUCTION', False)

# Variáveis de controle para evitar duplicações
ultimo_numero_por_roleta = {}
ultimo_timestamp_por_roleta = {}
# Dicionário para armazenar a assinatura visual única de cada atualização de roleta
assinaturas_roletas = {}
# Histórico de números por roleta para deduplicação rigorosa
historico_numeros_por_roleta = {}  # {id_roleta: [(numero, timestamp), ...]}
max_historico_por_roleta = 24      # Quantidade de números a manter no histórico
# Histórico da sequência completa de números por roleta
sequencias_por_roleta = {}  # {id_roleta: [num1, num2, num3, num4, num5]}

# Variáveis de controle adicionais para o scraping
roletas_verificadas = {}  # Timestamp da última verificação para cada roleta
roletas_com_ruido = {}    # Contador de ruído para cada roleta
limite_ignorar_roleta = 5  # Após quantos erros consecutivos ignoramos uma roleta por um tempo

# Intervalo mínimo para verificar a mesma roleta novamente (em segundos)
# Agora usaremos um sistema adaptativo que ajusta o intervalo com base na atividade
intervalo_base_verificacao = 5  # Intervalo base inicial
# Dicionário para armazenar intervalos adaptativos por roleta
intervalos_adaptativos = {}  # {id_roleta: intervalo_atual}
# Fator de ajuste para aumentar/diminuir o intervalo
fator_ajuste_intervalo = 1.5
# Intervalo mínimo e máximo
intervalo_min_absoluto = 3
intervalo_max_verificacao = 30
# Período em que consideramos uma roleta "ativa" após um novo número (em segundos)
periodo_roleta_ativa = 45
# Timestamps da última vez que cada roleta teve um novo número
ultima_atividade_roleta = {}  # {id_roleta: timestamp}
# Período de "castigo" para roletas com muito ruído (em segundos)
periodo_castigo_roleta = 120

def cfg_driver():
    """Driver minimalista"""
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")
    
    # Método rápido
    try:
        service = Service(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=opts)
    except:
        try:
            return webdriver.Chrome(options=opts)
        except Exception as e:
            print(f"Erro: {str(e)}")
            raise

def ext_numeros(driver, elemento):
    """Extrai números com abordagem adaptada à estrutura real das divs de roleta"""
    global ultima_atividade
    
    try:
        script = """
        return new Promise((resolve) => {
            const targetNode = arguments[0];
            let numChanges = 0;
            let stableReadings = [];
            let lastTopNumber = null;
            let lastTopColor = null;
            let lastCheckTimestamp = Date.now();
            let resolveTimeout = null;
            let lastSequence = [];  // Armazena a última sequência completa de números
            
            // Função para extrair o número mais recente (topo) com sua cor
            const extractTopNumber = () => {
                // Buscar especificamente pelo número preto no topo
                const topPreto = targetNode.querySelector(".fXLilg:first-child");
                if (topPreto) {
                    const texto = topPreto.textContent.trim();
                    if (/^\\d+$/.test(texto) && parseInt(texto) >= 0 && parseInt(texto) <= 36) {
                        return { numero: texto, cor: "preto" };
                    }
                }
                
                // Buscar especificamente pelo número vermelho no topo
                const topVermelho = targetNode.querySelector(".diKCfb:first-child");
                if (topVermelho) {
                    const texto = topVermelho.textContent.trim();
                    if (/^\\d+$/.test(texto) && parseInt(texto) >= 0 && parseInt(texto) <= 36) {
                        return { numero: texto, cor: "vermelho" };
                    }
                }
                
                // Caso não encontre os seletores específicos, tentar um método mais genérico
                const divsNumeros = targetNode.querySelectorAll(".sc-bCYfCC.diKCfb, .sc-bCYfCC.fXLilg");
                if (divsNumeros.length > 0) {
                    const primeiraDiv = divsNumeros[0];
                    const texto = primeiraDiv.textContent.trim();
                    const isVermelho = primeiraDiv.classList.contains("diKCfb");
                    const cor = isVermelho ? "vermelho" : "preto";
                    
                    if (/^\\d+$/.test(texto) && parseInt(texto) >= 0 && parseInt(texto) <= 36) {
                        return { numero: texto, cor: cor };
                    }
                }
                
                return null;
            };
            
            // Função para extrair a sequência completa de números (até 5)
            const extractFullSequence = () => {
                const sequence = [];
                const divsNumeros = targetNode.querySelectorAll(".sc-bCYfCC.diKCfb, .sc-bCYfCC.fXLilg");
                
                // Processamos todas as divs para obter a sequência completa
                divsNumeros.forEach(div => {
                    const texto = div.textContent.trim();
                    if (/^\\d+$/.test(texto) && parseInt(texto) >= 0 && parseInt(texto) <= 36) {
                        sequence.push(parseInt(texto));
                    }
                });
                
                return sequence;
            };
            
            // Função para comparar sequências e determinar se é um novo sorteio
            const isNewDraw = (newSequence, oldSequence) => {
                // Se não temos sequência anterior ou a nova está vazia, não podemos comparar
                if (!oldSequence.length || !newSequence.length) return false;
                
                // Um novo sorteio típico:
                // 1. Tem um novo número no topo (posição 0)
                // 2. Os outros números "desceram" uma posição
                
                // Para verificar se é um novo sorteio:
                // O novo número no topo (posição 0) não estava na sequência anterior
                // OU os números antigos desceram uma posição
                
                // Verificar se há um novo número no topo
                const novoNumeroNoTopo = newSequence[0] !== oldSequence[0];
                
                // Verificar se pelo menos alguns números da sequência anterior desceram uma posição
                let numDescidos = 0;
                const minLength = Math.min(newSequence.length, oldSequence.length) - 1;
                
                for (let i = 0; i < minLength; i++) {
                    // O número na posição i da nova sequência deve ser igual ao número na posição i-1 da sequência anterior
                    if (newSequence[i+1] === oldSequence[i]) {
                        numDescidos++;
                    }
                }
                
                // Consideramos um novo sorteio se o número do topo mudou E pelo menos alguns números desceram
                return novoNumeroNoTopo && numDescidos > 0;
            };
            
            // Função para finalizar e retornar o resultado
            const finishAndResolve = (number, fullSequence) => {
                if (resolveTimeout) {
                    clearTimeout(resolveTimeout);
                    resolveTimeout = null;
                }
                
                if (observer) {
                    observer.disconnect();
                }
                
                console.log(`Finalizando com número: ${number}, sequência completa: [${fullSequence.join(', ')}]`);
                resolve({
                    number: number,
                    sequence: fullSequence
                });
            };
            
            // Detectar mudança no número do topo
            const detectTopNumberChange = () => {
                const currentTop = extractTopNumber();
                if (!currentTop) return false;
                
                const currentSequence = extractFullSequence();
                const currentTime = Date.now();
                
                // Se não tínhamos número no topo antes, registrar este e retornar
                if (!lastTopNumber) {
                    lastTopNumber = currentTop.numero;
                    lastTopColor = currentTop.cor;
                    lastSequence = currentSequence;
                    lastCheckTimestamp = currentTime;
                    return false;
                }
                
                // Verificar se o número mudou
                if (currentTop.numero !== lastTopNumber) {
                    console.log(`Número no topo mudou: ${currentTop.numero} (${currentTop.cor}), anterior: ${lastTopNumber} (${lastTopColor})`);
                    console.log(`Nova sequência: [${currentSequence.join(', ')}], Anterior: [${lastSequence.join(', ')}]`);
                    
                    // Verificar se é um novo sorteio comparando as sequências
                    const isNewDrawDetected = isNewDraw(currentSequence, lastSequence);
                    if (isNewDrawDetected) {
                        console.log(`NOVO SORTEIO CONFIRMADO! Número: ${currentTop.numero}`);
                    } else {
                        console.log(`Mudança no topo, mas não parece ser um novo sorteio (possível reorganização da UI)`);
                    }
                    
                    // Atualizar as referências
                    const previousNumber = lastTopNumber;
                    lastTopNumber = currentTop.numero;
                    lastTopColor = currentTop.cor;
                    lastSequence = currentSequence;
                    lastCheckTimestamp = currentTime;
                    
                    // Verificar se o número já estava na nossa lista de leituras para evitar duplicações
                    const alreadyDetected = stableReadings.includes(currentTop.numero);
                    if (!alreadyDetected && isNewDrawDetected) {
                        // IMPORTANTE: Resolver imediatamente com o novo número quando temos certeza da mudança
                        // Mas adicionamos um pequeno delay para garantir estabilidade na detecção
                        setTimeout(() => {
                            // Verificar novamente o número atual para garantir estabilidade
                            const verificationTop = extractTopNumber();
                            const verificationSequence = extractFullSequence();
                            if (verificationTop && verificationTop.numero === currentTop.numero) {
                                // Número se manteve estável, podemos finalizar
                                finishAndResolve(currentTop.numero, verificationSequence);
                            }
                        }, 300); // Delay curto para estabilização
                        
                        return true;
                    } else {
                        if (alreadyDetected) {
                            console.log(`Número ${currentTop.numero} já foi detectado anteriormente, ignorando`);
                        }
                        return false;
                    }
                }
                
                return false;
            };
            
            // Capturar número inicial do topo (mais recente) e a sequência completa
            const initialTopNumber = extractTopNumber();
            const initialSequence = extractFullSequence();
            
            if (initialTopNumber) {
                console.log(`Número inicial no topo: ${initialTopNumber.numero} (${initialTopNumber.cor})`);
                console.log(`Sequência inicial: [${initialSequence.join(', ')}]`);
                lastTopNumber = initialTopNumber.numero;
                lastTopColor = initialTopNumber.cor;
                lastSequence = initialSequence;
                stableReadings.push(initialTopNumber.numero);
            }
            
            // Configurar observador para detectar mudanças no DOM
            const observer = new MutationObserver((mutations) => {
                // Apenas incrementar se houve mudanças reais no DOM
                let relevantChanges = false;
                
                // Verificação rápida primeiro - tenta detectar mudança diretamente
                const currentTopQuick = extractTopNumber();
                if (currentTopQuick && lastTopNumber && currentTopQuick.numero !== lastTopNumber) {
                    relevantChanges = true;
                } else {
                    // Se não detectou imediatamente, analisar as mutações
                    for (const mutation of mutations) {
                        // Verificar se a mutação envolve elementos relacionados aos números
                        if (mutation.target.classList && 
                            (mutation.target.classList.contains("diKCfb") || 
                             mutation.target.classList.contains("fXLilg") ||
                             mutation.target.classList.contains("sc-bCYfCC"))) {
                            relevantChanges = true;
                            break;
                        }
                        
                        // Verificar se a mutação afeta filhos que possam conter números
                        if (mutation.addedNodes.length > 0 || mutation.removedNodes.length > 0) {
                            relevantChanges = true;
                            break;
                        }
                    }
                }
                
                if (!relevantChanges) return;
                
                numChanges++;
                
                // Detectar se houve mudança no número do topo
                if (detectTopNumberChange()) {
                    // Se detectamos uma mudança real, adicionar o novo número
                    if (lastTopNumber) {
                        stableReadings.push(lastTopNumber);
                        // Manter histórico controlado
                        if (stableReadings.length > 5) {
                            stableReadings.shift();
                        }
                        console.log(`Mudança #${numChanges}: Novo número = ${lastTopNumber}`);
                    }
                }
            });
            
            // Iniciar a observação com configuração adequada
            observer.observe(targetNode, {
                childList: true,
                subtree: true,
                characterData: true,
                attributes: true,
                attributeFilter: ['class', 'style']
            });
            
            // Definir timeout como fallback, agora com tempo reduzido
            resolveTimeout = setTimeout(() => {
                observer.disconnect();
                console.log(`Timeout após ${numChanges} mudanças. Números detectados: ${stableReadings.join(', ')}`);
                
                // Se não temos nenhuma leitura, retornar vazio
                if (stableReadings.length === 0) {
                    resolve({number: null, sequence: []});
                    return;
                }
                
                // Se temos apenas uma leitura e é o número inicial, verificar se é válido
                if (stableReadings.length === 1) {
                    const num = stableReadings[0];
                    if (num && /^[0-9]{1,2}$/.test(num) && parseInt(num) <= 36) {
                        console.log(`Retornando único número válido: ${num}`);
                        resolve({number: num, sequence: lastSequence});
                    } else {
                        resolve({number: null, sequence: []});
                    }
                    return;
                }
                
                // Normalmente queremos o número mais recente que apareceu no topo
                const mostRecent = stableReadings[stableReadings.length - 1];
                console.log(`Timeout - usando número mais recente: ${mostRecent}`);
                resolve({number: mostRecent, sequence: lastSequence});
            }, 3000); // Reduzido para 3000ms
        });
        """
        
        result = driver.execute_script(script, elemento)
        if result and result.get('number'):
            ultima_atividade = time.time()
            return result.get('number'), result.get('sequence')
        return [], []
    
    except Exception as e:
        # Logar exceção para debug
        print(f"Erro ao extrair números: {str(e)}")
        return [], []

def ext_id(elemento):
    """ID minimalista"""
    try:
        classes = elemento.get_attribute("class")
        
        match = re.search(r'cy-live-casino-grid-item-(\d+)', classes)
        if match:
            return match.group(1)
        
        try:
            titulo = elemento.find_element(By.CSS_SELECTOR, ".cy-live-casino-grid-item-title").text
            return hashlib.md5(titulo.encode()).hexdigest()[:8]
        except:
            pass
            
        html = elemento.get_attribute("outerHTML")
        return hashlib.md5(html.encode()).hexdigest()[:10]
    
    except:
        return "unknown"

def cor_numero(num):
    """Cor do número"""
    if num == 0:
        return 'verde'
    
    vermelhos = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
    return 'vermelho' if num in vermelhos else 'preto'

def novo_numero(db, id_roleta, roleta_nome, numero):
    """Minimalista para novo número"""
    try:
        if isinstance(numero, str):
            num_int = int(re.sub(r'[^\d]', '', numero))
        else:
            num_int = int(numero)
        
        if not (0 <= num_int <= 36):
            return False
        
        cor = cor_numero(num_int)
        ts = datetime.now().isoformat()
        
        db.garantir_roleta_existe(id_roleta, roleta_nome)
        db.inserir_numero(id_roleta, roleta_nome, num_int, cor, ts)
        
        # Saída com nome completo e cor por extenso
        print(f"{roleta_nome}:{num_int}:{cor}")
        
        event_data = {
            "type": "new_number",
            "roleta_id": id_roleta,
            "roleta_nome": roleta_nome, 
            "numero": num_int,
            "timestamp": ts
        }
        event_manager.notify_clients(event_data, silent=True)
        
        return True
    except:
        return False

def processar_numeros(db, id_roleta, roleta_nome, numeros_novos):
    """Processamento de números com controle rigoroso de duplicações usando comparação de sequências"""
    global ultimo_numero_por_roleta, ultimo_timestamp_por_roleta, assinaturas_roletas, historico_numeros_por_roleta, sequencias_por_roleta
    global ultima_atividade_roleta, intervalos_adaptativos
    
    if not numeros_novos or len(numeros_novos) == 0:
        return False
    
    # Obter os últimos números do banco de dados
    existentes = []
    try:
        if hasattr(db, 'obter_numeros_recentes'):
            nums = db.obter_numeros_recentes(id_roleta, limite=10)
            existentes = [n.get('numero') for n in nums]
    except Exception as e:
        print(f"Erro ao obter números recentes: {str(e)}")
    
    # Tempo mínimo entre atualizações da mesma roleta (em segundos)
    # Usado apenas como medida de segurança, não como critério principal
    min_tempo_entre_atualizacoes = 5
    tempo_atual = time.time()
    
    # Inicializar o histórico para esta roleta se ainda não existir
    if id_roleta not in historico_numeros_por_roleta:
        historico_numeros_por_roleta[id_roleta] = []
    
    # Inicializar a sequência para esta roleta se ainda não existir
    if id_roleta not in sequencias_por_roleta:
        sequencias_por_roleta[id_roleta] = []
    
    ok = False
    for num_str in numeros_novos:
        try:
            if isinstance(num_str, str):
                n = int(re.sub(r'[^\d]', '', num_str))
            else:
                n = int(num_str)
            
            # Verificar se o número está no intervalo válido
            if not 0 <= n <= 36:
                print(f"Ignorando número inválido: {n}")
                continue
            
            # VERIFICAÇÃO 1: Criar uma assinatura para esta detecção
            # Combinação de roleta + número + timestamp arredondado para intervalos de 3 segundos
            timestamp_arredondado = int(tempo_atual / 3) * 3
            assinatura_atual = f"{id_roleta}_{n}_{timestamp_arredondado}"
            
            # Se já vimos esta assinatura muito recentemente, ignorar
            if assinatura_atual in assinaturas_roletas:
                ultimo_uso = assinaturas_roletas[assinatura_atual]
                if tempo_atual - ultimo_uso < min_tempo_entre_atualizacoes:
                    print(f"[DUPLICADO-ASSINATURA] Ignorando assinatura duplicada para {roleta_nome}: {n} (já vista há {tempo_atual - ultimo_uso:.1f}s)")
                    continue
            
            # VERIFICAÇÃO 2: Verificar se é o mesmo número que o último registrado para esta roleta
            ultimo_numero = ultimo_numero_por_roleta.get(id_roleta)
            ultimo_timestamp = ultimo_timestamp_por_roleta.get(id_roleta, 0)
            
            # Se for o mesmo número E tiver passado muito pouco tempo, ignorar
            # (isso é apenas uma salvaguarda contra duplicações extremamente rápidas)
            if (ultimo_numero == n and 
                (tempo_atual - ultimo_timestamp) < min_tempo_entre_atualizacoes):
                print(f"[DUPLICADO-ULTIMO] Ignorando número repetido {n} para {roleta_nome} (extremamente recente: {tempo_atual - ultimo_timestamp:.1f}s)")
                continue
            
            # VERIFICAÇÃO 3: Verificar a sequência atual de números da roleta
            sequencia_atual = sequencias_por_roleta.get(id_roleta, [])
            
            # Se há uma sequência anterior E este número já está no topo da sequência, é duplicado
            if sequencia_atual and n == sequencia_atual[0]:
                print(f"[DUPLICADO-SEQUENCIA] Ignorando número {n} para {roleta_nome} (já está no topo da sequência atual)")
                continue
            
            # VERIFICAÇÃO 4: Se for o mesmo número que o último do banco de dados, requer mais cuidado
            if existentes and n == existentes[0]:
                # Verificar se esse mesmo número foi extraído muito recentemente
                if (tempo_atual - ultimo_timestamp) < min_tempo_entre_atualizacoes:
                    print(f"[DUPLICADO-DB] Ignorando número duplicado {n} para {roleta_nome} (já existe no DB, muito recente)")
                    continue
                # Se passou tempo suficiente, pode ser um sorteio legítimo do mesmo número
                print(f"[REPETIDO-VÁLIDO] Aceitando número repetido {n} para {roleta_nome} (tempo suficiente: {tempo_atual - ultimo_timestamp:.1f}s)")
            
            # VERIFICAÇÃO FINAL: Verificar os números mais recentes no BD para esta roleta
            if existentes and n in existentes[:3] and tempo_atual - ultimo_timestamp < 10:
                # É muito improvável que o mesmo número apareça entre os últimos 3 em menos de 10 segundos
                print(f"[DUPLICADO-RECENTE] Ignorando número {n} para {roleta_nome} (já está entre os 3 últimos no DB em menos de 10s)")
                continue
            
            # Se chegou até aqui, o número é considerado novo
                if novo_numero(db, id_roleta, roleta_nome, n):
                print(f"[ACEITO] Número {n} para {roleta_nome} aceito como novo")
                
                # Atualizar o cache local
                ultimo_numero_por_roleta[id_roleta] = n
                ultimo_timestamp_por_roleta[id_roleta] = tempo_atual
                # Registrar a assinatura desta atualização
                assinaturas_roletas[assinatura_atual] = tempo_atual
                
                # Adicionar ao histórico de números
                historico_numeros_por_roleta[id_roleta].append((n, tempo_atual))
                # Manter apenas os últimos números no histórico
                if len(historico_numeros_por_roleta[id_roleta]) > max_historico_por_roleta:
                    historico_numeros_por_roleta[id_roleta] = historico_numeros_por_roleta[id_roleta][-max_historico_por_roleta:]
                
                # Atualizar a sequência da roleta (colocar o novo número no topo)
                sequencias_por_roleta[id_roleta] = [n] + sequencia_atual
                # Manter apenas os últimos 5 números na sequência
                if len(sequencias_por_roleta[id_roleta]) > 5:
                    sequencias_por_roleta[id_roleta] = sequencias_por_roleta[id_roleta][:5]
                
                # Limitar o tamanho do dicionário de assinaturas (evitar vazamento de memória)
                if len(assinaturas_roletas) > 1000:
                    # Remover as assinaturas mais antigas
                    assinaturas_antigas = sorted(
                        assinaturas_roletas.items(),
                        key=lambda x: x[1]
                    )[:500]  # Manter apenas as 500 mais recentes
                    for assinatura, _ in assinaturas_antigas:
                        if assinatura in assinaturas_roletas:
                            del assinaturas_roletas[assinatura]
                
                # NOVO: Atualizar o sistema adaptativo quando um novo número é aceito
                ultima_atividade_roleta[id_roleta] = tempo_atual
                # Reduzir o intervalo para esta roleta, pois está ativa
                if id_roleta in intervalos_adaptativos:
                    intervalos_adaptativos[id_roleta] = max(
                        intervalo_min_absoluto,
                        intervalos_adaptativos[id_roleta] / fator_ajuste_intervalo
                    )
                else:
                    intervalos_adaptativos[id_roleta] = intervalo_min_absoluto
                
                    ok = True
                
        except Exception as e:
            print(f"Erro ao processar número para {roleta_nome}: {str(e)}")
    
    return ok

def check_saude(driver):
    """Check mínimo"""
    global ultima_atividade, erros_consecutivos, driver_global
    
    if time.time() - ultima_atividade > 900:
        try:
            if driver:
                driver.quit()
            driver_global = cfg_driver()
            driver_global.get(CASINO_URL)
            ultima_atividade = time.time()
            erros_consecutivos = 0
            return driver_global
        except:
            erros_consecutivos += 1
    return driver

def retry(func, max_tries=3, delay=5, args=None, kwargs=None):
    """Retry minimalista"""
    if args is None: args = []
    if kwargs is None: kwargs = {}
    
    for t in range(max_tries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if t == max_tries - 1:
                raise e
            time.sleep(delay * (2 ** t))

def scrape_roletas(db, driver=None):
    """Scrape inteligente com sistema adaptativo de verificação"""
    global ultima_atividade, erros_consecutivos, driver_global
    global roletas_verificadas, roletas_com_ruido
    global intervalos_adaptativos, ultima_atividade_roleta
    
    try:
        drv = driver
        if drv is None:
            drv = retry(cfg_driver)
            driver_global = drv
        
        def navegar():
            drv.get(CASINO_URL)
            # Tempo maior para garantir carregamento completo
            time.sleep(8)
            return True
            
        retry(navegar)
        
        ciclo = 1
        erros = 0
        max_erros = 3
        ultimo_check = time.time()
        
        # IDs das roletas monitoradas
        ids = os.environ.get('ALLOWED_ROULETTES', '').split(',')
        if ids and ids[0].strip():
            print(f"Monitorando: {','.join([i[:5] for i in ids if i.strip()])}")
        
        # Inicializar lista de roletas para verificação prioritária
        roletas_prioritarias = set()
        todas_roletas = set()
        ultimo_log_adaptativos = time.time()
        
        while ciclo <= MAX_CICLOS or MAX_CICLOS == 0:
            try:
                # Verificar saúde do driver periodicamente
                if time.time() - ultimo_check > 300:
                    drv = check_saude(drv)
                    ultimo_check = time.time()
                    # Limpar o estado de roletas com ruído após verificação de saúde
                    roletas_com_ruido = {}
                
                def find_elements():
                    return drv.find_elements(By.CSS_SELECTOR, ".cy-live-casino-grid-item")
                
                # Buscar todas as roletas na página
                elementos = retry(find_elements)
                roletas_ativas = set()
                tempo_atual = time.time()
                
                # Verificar quais roletas devem sair do "castigo"
                for roleta_id in list(roletas_com_ruido.keys()):
                    ruido_info = roletas_com_ruido[roleta_id]
                    # Se passou o período de castigo e o contador é alto, reduzir pela metade
                    if tempo_atual - ruido_info['ultimo_erro'] > periodo_castigo_roleta and ruido_info['contador'] >= limite_ignorar_roleta:
                        roletas_com_ruido[roleta_id]['contador'] = max(1, ruido_info['contador'] // 2)
                        print(f"Roleta {roleta_id[:5]} saindo do castigo: contador reduzido para {roletas_com_ruido[roleta_id]['contador']}")
                
                # Primeiro, coletar todas as roletas disponíveis para priorização
                roletas_para_processar = []
                
                # Para cada elemento de roleta encontrado
                for elem in elementos:
                    try:
                        id_roleta = ext_id(elem)
                        todas_roletas.add(id_roleta)
                        
                        # Verificar se a roleta está permitida
                        if not roleta_permitida_por_id(id_roleta):
                            continue
                        
                        # Verificar se a roleta está em "castigo" por excesso de ruído
                        if id_roleta in roletas_com_ruido and roletas_com_ruido[id_roleta]['contador'] >= limite_ignorar_roleta:
                            # Verificar se já passou tempo suficiente desde o último erro
                            tempo_desde_ultimo_erro = tempo_atual - roletas_com_ruido[id_roleta]['ultimo_erro']
                            if tempo_desde_ultimo_erro < periodo_castigo_roleta:
                                # Ainda está em castigo, pular esta roleta
                                continue
                        
                        # Extrair o nome da roleta
                        titulo = elem.find_element(By.CSS_SELECTOR, ".cy-live-casino-grid-item-title").text.strip()
                        
                        # Verificar o intervalo adaptativo para esta roleta
                        intervalo_atual = intervalos_adaptativos.get(id_roleta, intervalo_base_verificacao)
                        
                        # Verificar se já verificamos esta roleta recentemente
                        tempo_desde_ultima_verificacao = tempo_atual - roletas_verificadas.get(id_roleta, 0)
                        
                        # Verificar se esta roleta está "ativa" (teve número recente)
                        roleta_ativa = id_roleta in ultima_atividade_roleta and (tempo_atual - ultima_atividade_roleta[id_roleta]) < periodo_roleta_ativa
                        
                        # Roletas ativas recebem prioridade e intervalos mais curtos
                        if roleta_ativa:
                            roletas_prioritarias.add(id_roleta)
                            # Se é uma roleta ativa, podemos reduzir um pouco o intervalo
                            if intervalo_atual > intervalo_min_absoluto:
                                intervalo_atual = max(intervalo_min_absoluto, intervalo_atual * 0.8)
                        else:
                            # Se não é ativa, aumentar gradualmente o intervalo
                            if intervalo_atual < intervalo_max_verificacao:
                                intervalo_atual = min(intervalo_max_verificacao, intervalo_atual * 1.05)
                        
                        # Atualizar o intervalo adaptativo
                        intervalos_adaptativos[id_roleta] = intervalo_atual
                        
                        # Verificar se é hora de processar esta roleta
                        if tempo_desde_ultima_verificacao >= intervalo_atual:
                            roletas_para_processar.append({
                                'id': id_roleta,
                                'titulo': titulo,
                                'elemento': elem,
                                'prioridade': 1 if roleta_ativa else 0,  # Roletas ativas têm prioridade maior
                                'ultima_verificacao': tempo_desde_ultima_verificacao
                            })
                    
                    except Exception as e:
                        # Erro ao extrair informações básicas da roleta, ignorar e continuar
                        print(f"Erro ao analisar roleta: {str(e)}")
                
                # Ordenar roletas para processar por prioridade e tempo desde a última verificação
                roletas_para_processar.sort(key=lambda r: (-r['prioridade'], -r['ultima_verificacao']))
                
                # Limitar o número de roletas verificadas por ciclo para balancear carga
                limite_roletas_por_ciclo = 3 if ciclo % 5 != 0 else 6  # A cada 5 ciclos, verificamos mais roletas
                
                # Processar roletas de acordo com a prioridade
                roletas_processadas = 0
                
                for info_roleta in roletas_para_processar[:limite_roletas_por_ciclo]:
                    try:
                        id_roleta = info_roleta['id']
                        titulo = info_roleta['titulo']
                        elem = info_roleta['elemento']
                        
                        roletas_ativas.add(titulo)
                        
                        print(f"Verificando roleta: {titulo} (intervalo adaptativo: {intervalos_adaptativos.get(id_roleta, intervalo_base_verificacao):.1f}s)")
                        
                        # Registrar esta verificação
                        roletas_verificadas[id_roleta] = tempo_atual
                        
                        # Extrair números
                        numero, sequencia = ext_numeros(drv, elem)
                        
                        # Se não encontrou números, isso pode ser ruído
                        if numero is None:
                            # Incrementar contador de ruído
                            if id_roleta not in roletas_com_ruido:
                                roletas_com_ruido[id_roleta] = {'contador': 1, 'ultimo_erro': tempo_atual, 'nome': titulo}
                            else:
                                roletas_com_ruido[id_roleta]['contador'] += 1
                                roletas_com_ruido[id_roleta]['ultimo_erro'] = tempo_atual
                            
                            if roletas_com_ruido[id_roleta]['contador'] >= limite_ignorar_roleta:
                                print(f"Roleta {titulo} ({id_roleta[:5]}) marcada como ruidosa (contador: {roletas_com_ruido[id_roleta]['contador']})")
                                
                                # Aumentar seu intervalo para verificações menos frequentes
                                if id_roleta in intervalos_adaptativos:
                                    intervalos_adaptativos[id_roleta] = min(
                                        intervalo_max_verificacao * 2,  # Pode ultrapassar o máximo normal para roletas problemáticas
                                        intervalos_adaptativos[id_roleta] * fator_ajuste_intervalo
                                    )
                            continue
                        
                        # Se encontrou números, reduzir o contador de ruído (se existir)
                        if id_roleta in roletas_com_ruido and roletas_com_ruido[id_roleta]['contador'] > 0:
                            roletas_com_ruido[id_roleta]['contador'] = max(0, roletas_com_ruido[id_roleta]['contador'] - 1)
                            if roletas_com_ruido[id_roleta]['contador'] == 0:
                                print(f"Roleta {titulo} ({id_roleta[:5]}) não é mais considerada ruidosa")
                        
                        # Processar os números encontrados
                        sucesso = processar_numeros(db, id_roleta, titulo, [numero])
                        
                        # Atualizar timestamp de atividade apenas se processou números
                        if sucesso:
                            ultima_atividade = tempo_atual
                        erros_consecutivos = 0
                            
                            # Esta roleta se tornou ativa, garantir que ela seja verificada com frequência
                            roletas_prioritarias.add(id_roleta)
                        
                        roletas_processadas += 1
                    
                    except Exception as e:
                        print(f"Erro ao processar roleta {info_roleta.get('titulo', 'desconhecida')}: {str(e)}")
                        erros += 1
                
                # Logar periodicamente informações sobre os intervalos adaptativos
                if tempo_atual - ultimo_log_adaptativos > 60:  # A cada minuto
                    print("=== SISTEMA ADAPTATIVO ===")
                    print(f"Roletas ativas: {len(roletas_prioritarias)}/{len(todas_roletas)}")
                    # Mostrar roletas com intervalo mais baixo (potencialmente mais ativas)
                    roletas_rapidas = sorted(
                        [(id, intervalo) for id, intervalo in intervalos_adaptativos.items() if id in todas_roletas],
                        key=lambda x: x[1]
                    )[:5]
                    
                    if roletas_rapidas:
                        print("Top 5 roletas mais frequentes:")
                        for id_r, intervalo in roletas_rapidas:
                            nome_r = "Desconhecida"
                            for info in roletas_para_processar:
                                if info['id'] == id_r:
                                    nome_r = info['titulo']
                                    break
                            print(f"  - {nome_r} ({id_r[:5]}): {intervalo:.1f}s")
                    
                    ultimo_log_adaptativos = tempo_atual
                
                # Se não encontrou nenhuma roleta ativa após várias tentativas, recarregar a página
                if not roletas_ativas and ciclo % 100 == 0 and erros >= max_erros:
                    print("Nenhuma roleta ativa encontrada, recarregando página...")
                    retry(navegar)
                    erros = 0
                
                # Ajustar o intervalo entre ciclos com base no número de roletas processadas
                # Mais roletas processadas = intervalo menor, mantendo eficiência
                if roletas_processadas > 0:
                    sleep_time = random.uniform(2, 4)  # Intervalo rápido quando há roletas para verificar
                else:
                    sleep_time = random.uniform(3, 5)  # Intervalo maior quando não há muito o que verificar
                
                time.sleep(sleep_time)
                ciclo += 1
                erros = 0
                
            except Exception as e:
                print(f"Erro no ciclo de scraping: {str(e)}")
                erros += 1
                erros_consecutivos += 1
                
                if erros >= max_erros or erros_consecutivos >= MAX_ERROS_CONSECUTIVOS:
                    try:
                        print(f"Reiniciando driver após {erros_consecutivos} erros consecutivos")
                        if drv:
                            drv.quit()
                        drv = retry(cfg_driver)
                        driver_global = drv
                        retry(navegar)
                        erros = 0
                        erros_consecutivos = 0
                    except Exception as e:
                        print(f"Erro ao reiniciar driver: {str(e)}")
                        time.sleep(30)
    
    except Exception as e:
        print(f"Erro fatal no scraping: {str(e)}")
    
    finally:
        if driver is None and 'drv' in locals() and drv:
            try:
                drv.quit()
            except:
                pass

def simulate_roulette_data(db):
    """Simulador minimalista"""
    roletas = [
        {"id": "vctlz3AoNaGCzxJi", "nome": "Auto-Roulette"},
        {"id": "LightningTable01", "nome": "Lightning Roulette"},
        {"id": "7x0b1tgh7agmf6hv", "nome": "Roulette Live"}
    ]
    
    print(f"Simulando: {','.join([r['nome'] for r in roletas])}")
    
    while True:
        try:
            roleta = random.choice(roletas)
            rid = roleta["id"]
            nome = roleta["nome"]
            
            num = random.randint(0, 36)
            cor = cor_numero(num)
            
            # Saída com nome completo e cor por extenso
            print(f"{nome}:{num}:{cor}")
            
            db.garantir_roleta_existe(rid, nome)
            ts = datetime.now().isoformat()
            db.inserir_numero(rid, nome, num, cor, ts)
            
            event_data = {
                "type": "new_number",
                "roleta_id": rid,
                "roleta_nome": nome,
                "numero": num,
                "timestamp": ts,
                "simulado": True
            }
            event_manager.notify_clients(event_data, silent=True)
            
            time.sleep(random.randint(1, 3))
            
        except:
            time.sleep(5)

# Patch minimalista
if hasattr(event_manager, 'notify_clients') and 'silent' not in event_manager.notify_clients.__code__.co_varnames:
    def notify_clients_patched(event_data, silent=True):
        event_manager.event_queue.put(event_data)
        for client_queue in event_manager.clients[:]:
            try:
                client_queue.put(event_data)
            except:
                event_manager.unregister_client(client_queue)
    
    event_manager.notify_clients = notify_clients_patched

# Exports
__all__ = ['scrape_roletas', 'simulate_roulette_data', 'check_saude', 'cfg_driver'] 