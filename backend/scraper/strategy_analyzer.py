from enum import Enum
from terminal_table import TERMINAL_TABLE
import logging
from datetime import datetime

class State(Enum):
    MORTO = "MORTO"
    NEUTRAL = "NEUTRAL"
    TRIGGER = "TRIGGER"
    GALE = "GALE"
    POST_GALE_NEUTRAL = "POST_GALE_NEUTRAL"

class StrategyAnalyzer:
    def __init__(self, titulo_roleta=None):
        self.current_state = State.NEUTRAL
        self.trigger_number = -1
        self.previous_trigger = -1
        self.result_processed = False
        self.win_count = 0
        self.loss_count = 0
        self.history = []
        self.terminal_table = TERMINAL_TABLE
        self.titulo_roleta = titulo_roleta
        self.last_processed_numbers = set()  # Para controlar quais números já foram processados
        
    def process_number(self, number):
        """
        Processa um novo número seguindo a máquina de estados da estratégia
        """
        if number is None or not isinstance(number, int) or not (0 <= number <= 36):
            logging.warning(f"Número inválido ignorado: {number}")
            return
            
        self.history.append(number)
        old_state = self.current_state
        logging.info(f"Processando número: {number} | Estado atual: {self.current_state.value}")
        
        if self.current_state == State.MORTO:
            self._handle_morto_state()
            if self.current_state == State.NEUTRAL:
                self._handle_neutral_state(number)
        elif self.current_state == State.NEUTRAL:
            self._handle_neutral_state(number)
        elif self.current_state == State.TRIGGER:
            self._handle_trigger_state(number)
        elif self.current_state == State.POST_GALE_NEUTRAL:
            self._handle_post_gale_state(number)
            
        if old_state != self.current_state:
            logging.info(f"Estado alterado: {old_state.value} -> {self.current_state.value}")

            
    def _handle_morto_state(self):
        """Processa o estado MORTO"""
        logging.info("Estado MORTO: Reiniciando para NEUTRAL")
        self.current_state = State.NEUTRAL
        self.result_processed = False
        
    def _handle_neutral_state(self, number):
        """Processa o estado NEUTRAL"""
        if number is None or not isinstance(number, int) or not (0 <= number <= 36):
            logging.warning(f"Número inválido no estado NEUTRAL: {number}")
            return
            
        self.trigger_number = number
        
        if self.trigger_number in self.terminal_table:
            terminals = self.terminal_table[self.trigger_number][:3]  # Pegando apenas os 3 primeiros números
            terminals_str = ','.join(map(str, terminals))
            logging.info(f"Número gatilho {self.trigger_number} encontrado. Terminais: {terminals_str}")
            self.analyze_terminals(self.trigger_number)
        else:
            logging.warning(f"Número gatilho {self.trigger_number} não encontrado na tabela.")
            
        self.current_state = State.TRIGGER
        
    def _handle_trigger_state(self, number):
        """Processa o estado TRIGGER"""
        if number is None or not isinstance(number, int) or not (0 <= number <= 36):
            logging.warning(f"Número inválido no estado TRIGGER: {number}")
            return
            
        if self.trigger_number not in self.terminal_table:
            logging.warning(f"Gatilho {self.trigger_number} não está na tabela de terminais")
            self.current_state = State.NEUTRAL
            return
            
        terminals = self.terminal_table[self.trigger_number]
        
        if number in terminals:
            logging.info(f"WIN! Número {number} está nos terminais de {self.trigger_number}")
            self.process_result(True)
            self.current_state = State.MORTO
        else:
            logging.info(f"GALE! Número {number} não está nos terminais de {self.trigger_number}")
            self.previous_trigger = self.trigger_number
            self.current_state = State.POST_GALE_NEUTRAL
            
    def _handle_post_gale_state(self, number):
        """Processa o estado POST_GALE_NEUTRAL"""
        if number is None or not isinstance(number, int) or not (0 <= number <= 36):
            logging.warning(f"Número inválido no estado POST_GALE_NEUTRAL: {number}")
            return
            
        if self.previous_trigger not in self.terminal_table:
            logging.warning(f"Gatilho anterior {self.previous_trigger} não está na tabela de terminais")
            self.current_state = State.NEUTRAL
            return
            
        terminals = self.terminal_table[self.previous_trigger]
        
        if number in terminals:
            logging.info(f"WIN após GALE! Número {number} está nos terminais de {self.previous_trigger}")
            self.process_result(True)
        else:
            logging.info(f"LOSS após GALE! Número {number} não está nos terminais de {self.previous_trigger}")
            self.process_result(False)
            
        self.current_state = State.MORTO
        
    def process_result(self, is_win):
        """Processa o resultado (vitória ou derrota)"""
        if is_win:
            self.win_count += 1
            logging.info(f"VITÓRIA registrada! Total de vitórias: {self.win_count}")
        else:
            self.loss_count += 1
            logging.info(f"DERROTA registrada! Total de derrotas: {self.loss_count}")
        
        logging.info(f"Resultado processado: {'Vitória' if is_win else 'Derrota'}")
        logging.info(f"Placar: {self.win_count}W / {self.loss_count}L")
        self.result_processed = True
        
    def analyze_terminals(self, trigger_number):
        """Analisa os terminais para o número gatilho"""
        if trigger_number in self.terminal_table:
            terminals = self.terminal_table[trigger_number][:3]  # Pegando apenas os 3 primeiros números
            logging.info(f"Analisando terminais para {trigger_number}: {terminals}")
            return terminals
        return []
        
    def get_status(self):
        """Retorna o status atual da estratégia"""
        # Obter os terminais do número gatilho atual
        terminais_atuais = []
        soma_terminais = 0
        if self.trigger_number in self.terminal_table:
            terminais_atuais = self.terminal_table[self.trigger_number][:3]  # Apenas 3 primeiros números
            soma_terminais = sum(terminais_atuais)
        
        # Obter os terminais do número gatilho anterior (se houver)
        terminais_anteriores = []
        soma_terminais_anteriores = 0
        if self.previous_trigger in self.terminal_table:
            terminais_anteriores = self.terminal_table[self.previous_trigger][:3]  # Apenas 3 primeiros números
            soma_terminais_anteriores = sum(terminais_anteriores)
        
        return {
            "estado": self.current_state.value,
            "numero_gatilho": self.trigger_number,
            "numero_gatilho_anterior": self.previous_trigger,
            "terminais_gatilho": terminais_atuais,
            "soma_terminais_gatilho": soma_terminais,
            "terminais_gatilho_anterior": terminais_anteriores,
            "soma_terminais_anterior": soma_terminais_anteriores,
            "vitorias": self.win_count,
            "derrotas": self.loss_count,
            "total_jogadas": len(self.history),
            "ultimos_numeros": self.history[-1000:] if self.history else []
        }

    def add_numbers(self, numbers):
        """
        Adiciona e processa novos números
        Retorna True se algum número novo foi processado, False caso contrário
        """
        if not numbers:
            return False
            
        has_new_numbers = False
        
        for num_str in numbers:
            try:
                # Tratamento para remover impurezas potenciais no texto do número
                if isinstance(num_str, str):
                    # Remove caracteres não numéricos, exceto dígitos e ponto/vírgula
                    clean_num_str = ''.join(ch for ch in num_str if ch.isdigit() or ch in ['.', ','])
                    # Caso não reste nada após a limpeza, pule
                    if not clean_num_str:
                        logging.warning(f"Número inválido após limpeza: '{num_str}'")
                        continue
                    # Substitui vírgula por ponto e converte para inteiro
                    clean_num_str = clean_num_str.replace(',', '.')
                    # Se tiver ponto decimal, converta para float e depois para int
                    if '.' in clean_num_str:
                        num = int(float(clean_num_str))
                    else:
                        num = int(clean_num_str)
                else:
                    # Se já for um número, converta para int
                    num = int(num_str)
                
                # Verifica se é um número válido de roleta (0-36)
                if 0 <= num <= 36:
                    # Chave para o dicionário last_processed_numbers deve ser string para consistência
                    key = str(num)
                    if key not in self.last_processed_numbers:
                        logging.info(f"Processando novo número: {num}")
                        self.process_number(num)
                        self.last_processed_numbers.add(key)
                        has_new_numbers = True
                    else:
                        logging.debug(f"Número já processado recentemente: {num}")
                else:
                    logging.warning(f"Número fora do intervalo válido (0-36): {num}")
            except Exception as e:
                logging.warning(f"Erro ao processar valor '{num_str}': {str(e)}")
                
        # Limita o tamanho do conjunto para evitar crescimento indefinido
        if len(self.last_processed_numbers) > 100:
            self.last_processed_numbers = set(list(self.last_processed_numbers)[-50:])
            
        return has_new_numbers
        
    def get_data(self):
        """
        Retorna os dados da roleta para salvar no Supabase
        """
        status = self.get_status()
        return {
            "titulo": self.titulo_roleta,
            "numeros": self.history[-1000:] if self.history else [],  # Últimos 1000 números (era 20)
            "status": status["estado"],
            "numero_gatilho": status["numero_gatilho"],
            "terminais_gatilho": status["terminais_gatilho"],
            "estatisticas": {
                "vitorias": status["vitorias"],
                "derrotas": status["derrotas"],
                "total": len(self.history)
            },
            "ultima_atualizacao": datetime.now().isoformat(),
            # Adicionar dados de estratégia no formato esperado pelo Supabase
            "estrategia": {
                "estado": status["estado"],
                "numero_gatilho": status["numero_gatilho"],
                "numero_gatilho_anterior": status["numero_gatilho_anterior"],
                "terminais_gatilho": status["terminais_gatilho"],
                "terminais_gatilho_anterior": status["terminais_gatilho_anterior"],
                "vitorias": status["vitorias"],
                "derrotas": status["derrotas"],
                "sugestao_display": self._gerar_sugestao_display(status)
            }
        }
        
    def _gerar_sugestao_display(self, status):
        """
        Gera uma string de sugestão para exibição baseada no estado atual
        """
        if status["estado"] == "NEUTRAL":
            return "AGUARDANDO GATILHO"
        elif status["estado"] == "TRIGGER":
            # Mostrar apenas os 3 primeiros terminais
            terminais = status["terminais_gatilho"][:3] if status["terminais_gatilho"] else []
            if terminais:
                return f"{','.join(map(str, terminais))}"
            else:
                return ""
        elif status["estado"] == "POST_GALE_NEUTRAL":
            # Mostrar apenas os 3 primeiros terminais do gatilho anterior
            terminais = status["terminais_gatilho_anterior"][:3] if status["terminais_gatilho_anterior"] else []
            if terminais:
                return f"{','.join(map(str, terminais))}"
            else:
                return ""
        elif status["estado"] == "MORTO":
            return "AGUARDANDO PRÓXIMO CICLO"
        else:
            return ""