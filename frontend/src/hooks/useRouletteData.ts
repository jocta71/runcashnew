import { useState, useEffect, useCallback } from 'react';
import SocketService, { RouletteNumberEvent } from '@/services/SocketService';
import { fetchRouletteLatestNumbers } from '@/integrations/api/rouletteService';
import { toast } from '@/components/ui/use-toast';

// Interface para número da roleta
export interface RouletteNumber {
  numero: number;
  cor: string;
  timestamp: string;
}

// Interface para o resultado do hook
export interface UseRouletteDataResult {
  numbers: RouletteNumber[];
  loading: boolean;
  error: string | null;
  isConnected: boolean;
  hasData: boolean;
}

/**
 * Função auxiliar para determinar a cor de um número da roleta
 */
const determinarCorNumero = (numero: number): string => {
  if (numero === 0) return 'verde';
  
  // Números vermelhos na roleta europeia
  const numerosVermelhos = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
  return numerosVermelhos.includes(numero) ? 'vermelho' : 'preto';
};

/**
 * Hook para obter e atualizar dados da roleta em tempo real
 * @param roletaId - ID da roleta
 * @param roletaNome - Nome da roleta (para subscrição de eventos)
 * @param limit - Limite de números a serem exibidos
 * @returns Objeto com números, estado de carregamento, erro e status de conexão
 */
export function useRouletteData(
  roletaId: string, 
  roletaNome: string, 
  limit: number = 50
): UseRouletteDataResult {
  const [numbers, setNumbers] = useState<RouletteNumber[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [hasData, setHasData] = useState<boolean>(false);
  
  // Carregar números iniciais da API
  useEffect(() => {
    const loadInitialData = async () => {
      try {
        setLoading(true);
        
        // Obter números iniciais da API (retorna um array de números)
        const numerosArray = await fetchRouletteLatestNumbers(roletaId, limit);
        
        if (numerosArray && numerosArray.length > 0) {
          // Converter array de números para o formato RouletteNumber
          const formattedNumbers: RouletteNumber[] = numerosArray.map((numero, index) => {
            // Para números da API que não têm timestamp, usar timestamps decrescentes fictícios
            // para simular a ordem cronológica (mais recente primeiro)
            const now = new Date();
            const timestamp = new Date(now.getTime() - (index * 60000)).toISOString(); // 1 minuto de diferença
            
            return {
              numero,
              cor: determinarCorNumero(numero),
              timestamp
            };
          });
          
          setNumbers(formattedNumbers);
          setHasData(true);
          console.log(`[useRouletteData] Carregados ${formattedNumbers.length} números iniciais para ${roletaNome}`);
        } else {
          setHasData(false);
          console.log(`[useRouletteData] Nenhum número encontrado no banco de dados para ${roletaNome}`);
          
          // Notificar o usuário que não há dados reais
          toast({
            title: `Sem dados para ${roletaNome}`,
            description: "Não foram encontrados números para esta roleta no MongoDB",
            variant: "destructive"
          });
        }
        
        setLoading(false);
      } catch (err: any) {
        console.error(`[useRouletteData] Erro ao carregar dados iniciais: ${err.message}`);
        setError(`Erro ao carregar dados: ${err.message}`);
        setLoading(false);
        setHasData(false);
      }
    };
    
    loadInitialData();
  }, [roletaId, roletaNome, limit]);
  
  // Callback para processar eventos de novos números
  const handleNewNumber = useCallback((event: RouletteNumberEvent) => {
    if (event.roleta_id !== roletaId) return;
    
    console.log(`[useRouletteData] Novo número recebido: ${event.numero} (${event.roleta_nome})`);
    
    setNumbers(prev => {
      // Verificar se o número já existe (evitar duplicatas)
      const isDuplicate = prev.some(num => 
        num.numero === event.numero && 
        num.timestamp === event.timestamp
      );
      
      if (isDuplicate) {
        console.log(`[useRouletteData] Ignorando número duplicado: ${event.numero}`);
        return prev;
      }
      
      // Adicionar o novo número no início do array
      const newNumber: RouletteNumber = {
        numero: event.numero,
        cor: event.cor || determinarCorNumero(event.numero),
        timestamp: event.timestamp
      };
      
      setHasData(true);
      
      // Limitar ao número máximo de elementos
      return [newNumber, ...prev].slice(0, limit);
    });
    
    // Atualizar status de conexão
    setIsConnected(true);
  }, [roletaId, limit]);
  
  // Subscrever para eventos da roleta
  useEffect(() => {
    const socketService = SocketService.getInstance();
    
    // Subscrever para eventos
    socketService.subscribe(roletaNome, handleNewNumber);
    
    // Atualizar status de conexão
    setIsConnected(socketService.isSocketConnected());
    
    return () => {
      // Remover subscrição ao desmontar
      socketService.unsubscribe(roletaNome, handleNewNumber);
    };
  }, [roletaNome, handleNewNumber]);
  
  return { numbers, loading, error, isConnected, hasData };
} 