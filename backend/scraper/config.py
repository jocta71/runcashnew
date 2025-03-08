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
    
    # Se a variável não estiver definida ou estiver vazia, permitir todas
    if not roletas_permitidas:
        return True
    
    # Dividir a string por vírgulas para obter a lista de roletas permitidas
    lista_permitidas = [r.strip() for r in roletas_permitidas.split(',')]
    
    # Verificar se o ID da roleta está na lista de permitidas
    return id_roleta in lista_permitidas
