import os
from dotenv import load_dotenv
import logging

# Carregar variáveis de ambiente
load_dotenv()

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('roulette_scraper')

# URL do cassino
CASINO_URL = "https://es.888casino.com/live-casino/#filters=live-roulette"

# Configuração do Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Lista de IDs de roletas permitidas
DEFAULT_ALLOWED_ROULETTES = "2010016,2380335,2010065,2010096,2010017,2010098"
ALLOWED_ROULETTES = os.getenv("ALLOWED_ROULETTES", DEFAULT_ALLOWED_ROULETTES).split(",")

# Configurações gerais
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "5"))
MAX_CICLOS = 1000  # Número máximo de ciclos antes de reiniciar o driver

def roleta_permitida_por_id(id_roleta):
    """Verifica se a roleta está na lista de roletas permitidas"""
    # Se a lista estiver vazia ou o primeiro elemento for vazio, permite todas
    if not ALLOWED_ROULETTES or not ALLOWED_ROULETTES[0]:
        return True
    
    # Verifica se o ID está na lista
    return id_roleta in ALLOWED_ROULETTES
