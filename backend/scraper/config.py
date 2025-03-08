import os
from dotenv import load_dotenv
import logging

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

# URL base do cassino para navegação Selenium
CASINO_URL = os.getenv('CASINO_URL', 'https://www.bugabet.com/casino')

# URLs das APIs do cassino (para acesso direto sem Selenium)
CASINO_API_URLS = {
    "Roleta Brasileira": os.getenv('CASINO_API_BR', 'https://api.bugabet.com/api/v1/data/roulette/br'),
    "Roleta Europeia": os.getenv('CASINO_API_EU', 'https://api.bugabet.com/api/v1/data/roulette/eu')
}

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
