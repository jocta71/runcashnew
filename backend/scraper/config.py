import os
import logging
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Configurar logging
logger = logging.getLogger('roulette_scraper')
logger.setLevel(logging.INFO)

# Criar um handler para console
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# Criar um formatador
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)

# Adicionar o handler ao logger
logger.addHandler(console_handler)

# Máximo de ciclos (0 = infinito)
MAX_CICLOS = 0

# Intervalo de scraping em minutos (padrão: 5 minutos)
SCRAPE_INTERVAL_MINUTES = int(os.getenv('SCRAPE_INTERVAL_MINUTES', 5))

# Supabase
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# URL do cassino
casino_url_env = os.getenv('CASINO_URL', 'https://es.888casino.com/live-casino/#filters=live-roulette')
# Sanitizar a URL removendo espaços e símbolos indesejados
CASINO_URL = casino_url_env.strip()
if CASINO_URL.startswith('='):
    CASINO_URL = CASINO_URL[1:]

# Função para verificar se uma roleta é permitida
def roleta_permitida_por_id(id_roleta):
    roletas_permitidas = os.getenv('ALLOWED_ROULETTES', '')
    
    # Se o ID da roleta não for válido, rejeitar imediatamente
    if not id_roleta or not isinstance(id_roleta, str) or id_roleta.strip() == '':
        logger.warning(f"ID de roleta inválido: {id_roleta}")
        return False
    
    # Se a variável de ambiente estiver vazia, usar lista padrão de roletas permitidas
    if not roletas_permitidas:
        # Lista padrão de roletas permitidas - mantém consistência com o frontend
        roletas_padrao = [
            "2010016",  # Immersive Roulette
            "2380335",  # Brazilian Mega Roulette
            "2010065",  # Bucharest Auto-Roulette
            "2010096",  # Speed Auto Roulette
            "2010017",  # Auto-Roulette
            "2010098"   # Auto-Roulette VIP
        ]
        logger.info(f"Usando lista padrão de roletas permitidas: {roletas_padrao}")
        return id_roleta in roletas_padrao
    
    # Dividir a string por vírgulas para obter a lista de roletas permitidas
    lista_permitidas = [r.strip() for r in roletas_permitidas.split(',')]
    
    # Verificar se o ID da roleta está na lista de permitidas
    resultado = id_roleta in lista_permitidas
    
    # Registrar no log se a roleta foi permitida ou não
    if resultado:
        logger.debug(f"Roleta permitida: {id_roleta}")
    else:
        logger.debug(f"Roleta ignorada: {id_roleta} (não está na lista de permitidas)")
    
    return resultado
