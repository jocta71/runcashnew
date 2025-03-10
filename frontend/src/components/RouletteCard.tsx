import { TrendingUp, ChartBar } from 'lucide-react';
import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { toast } from '@/components/ui/use-toast';
import { useNavigate } from 'react-router-dom';
import { strategies, numberGroups } from './roulette/constants';
import LastNumbers from './roulette/LastNumbers';
import WinRateDisplay from './roulette/WinRateDisplay';
import RouletteTrendChart from './roulette/RouletteTrendChart';
import SuggestionDisplay from './roulette/SuggestionDisplay';
import RouletteActionButtons from './roulette/RouletteActionButtons';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import RouletteStatsModal from './roulette/RouletteStatsModal';
import { fetchRouletteLatestNumbersByName } from '@/integrations/api/rouletteService';

interface RouletteCardProps {
  name: string;
  lastNumbers: number[];
  wins: number;
  losses: number;
  trend: { value: number }[];
}

// Objeto global para armazenar estado persistente entre remontagens
const persistentState: Record<string, {
  lastNumbers: number[],
  lastUpdated: number,
  hasLoaded: boolean
}> = {};

const RouletteCard = ({ name, lastNumbers: initialLastNumbers, wins, losses, trend }: RouletteCardProps) => {
  const navigate = useNavigate();
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [suggestion, setSuggestion] = useState<number[]>([]);
  const [isBlurred, setIsBlurred] = useState(false);
  const [currentStrategy, setCurrentStrategy] = useState(strategies[0]);
  const [selectedGroup, setSelectedGroup] = useState<string>("grupo-123");
  
  // Verificar se o nome da roleta é válido
  const roletaNome = name || "Roleta Desconhecida";
  
  // Inicializamos o estado a partir do estado persistente, se existir
  const [lastNumbers, setLastNumbers] = useState<number[]>(() => {
    if (persistentState[roletaNome]?.lastNumbers?.length > 0) {
      console.log(`[PERSISTÊNCIA][${roletaNome}] Recuperando estado salvo:`, 
        persistentState[roletaNome].lastNumbers.length);
      return persistentState[roletaNome].lastNumbers;
    }
    return initialLastNumbers || [];
  });
  
  const [previousLastNumber, setPreviousLastNumber] = useState<number | null>(null);
  
  // Usar estado persistente para carregamento também
  const [isLoading, setIsLoading] = useState<boolean>(() => {
    if (persistentState[roletaNome]?.hasLoaded) {
      return false;
    }
    return true;
  });
  
  const [dataSeeded, setDataSeeded] = useState<boolean>(() => {
    return !!persistentState[roletaNome]?.hasLoaded;
  });
  
  const [statsOpen, setStatsOpen] = useState(false);
  const [usingSupabaseData, setUsingSupabaseData] = useState(false);
  
  // Referência para o intervalo de polling (desativado por padrão)
  const pollingIntervalRef = useRef<number | null>(null);
  
  // Referência para a assinatura do Supabase Realtime
  const supabaseSubscriptionRef = useRef<any>(null);
  
  // Registra o componente como montado
  const isMounted = useRef(true);
  
  // Controle para ativar/desativar o polling
  const ENABLE_POLLING = false; // Desativado por padrão
  const POLLING_INTERVAL = 15000; // 15 segundos

  // Função para verificar se a página está visível
  const isDocumentVisible = () => document.visibilityState === 'visible';
  
  // Verificar se os componentes estão congelados (bloqueados pelo sistema anti-recarregamento)
  const areComponentsFrozen = () => {
    return (window as any).__REACT_COMPONENTS_FROZEN === true;
  };
  
  // React Strict Mode pode estar causando renderizações duplas
  // Usando useEffect com uma flag de "já renderizou" para evitar dupla renderização
  const didRenderRef = useRef(false);
  
  // Evitar completamente qualquer piscar durante atualizações
  useEffect(() => {
    // Este bloco executará apenas uma vez por montagem do componente
    if (!didRenderRef.current) {
      didRenderRef.current = true;
      
      // Adicionar classe para evitar transições no primeiro render
      const card = document.querySelector(`[data-roulette-name="${roletaNome}"]`) as HTMLElement;
      if (card) {
        card.classList.add('no-transition');
        // Remover a classe após o render inicial para permitir transições futuras
        setTimeout(() => {
          card.classList.remove('no-transition');
        }, 300);
      }
    }
  }, []);
  
  // Desabilitar todos os indicadores de carregamento ou animações
  useEffect(() => {
    const disableLoadingIndicators = () => {
      // Evitar o indicador de carregamento completamente
      setIsLoading(false);
      
      // Se tivermos dados no estado persistente, usar imediatamente
      if (persistentState[roletaNome]?.lastNumbers?.length > 0) {
        setLastNumbers(persistentState[roletaNome].lastNumbers);
        setDataSeeded(true);
      } else if (initialLastNumbers && initialLastNumbers.length > 0) {
        setLastNumbers(initialLastNumbers);
        setDataSeeded(true);
      }
    };
    
    // Desabilitar imediatamente
    disableLoadingIndicators();
    
    // Também desabilitar quando o documento se tornar visível
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        disableLoadingIndicators();
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [roletaNome, initialLastNumbers]);
  
  // Persistir o estado sempre que lastNumbers mudar
  useEffect(() => {
    if (lastNumbers.length > 0) {
      persistentState[roletaNome] = {
        lastNumbers,
        lastUpdated: Date.now(),
        hasLoaded: true
      };
    }
  }, [lastNumbers, roletaNome]);

  // Tratamento para eventos de retorno à página
  useEffect(() => {
    const handleReturnToPage = (event: any) => {
      console.log(`[EVENTO][${roletaNome}] Retorno à página detectado, tempo fora:`, 
        Math.round(event.detail.timeAway / 1000), 'segundos');
        
      // Se os componentes estão congelados, não fazer nada
      if (areComponentsFrozen()) {
        console.log(`[EVENTO][${roletaNome}] Componentes congelados, mantendo estado atual`);
        return;
      }
      
      // Verificar se precisamos atualizar dados
      const lastUpdated = persistentState[roletaNome]?.lastUpdated || 0;
      const now = Date.now();
      const tenMinutes = 10 * 60 * 1000;
      
      if (now - lastUpdated > tenMinutes && document.visibilityState === 'visible') {
        console.log(`[EVENTO][${roletaNome}] Atualizando dados antigos silenciosamente`);
        
        // Atualização silenciosa em segundo plano, sem alterar UI
        fetchRouletteLatestNumbersByName(roletaNome, 20)
          .then(numbers => {
            if (!isMounted.current) return;
            
            if (numbers && numbers.length > 0) {
              const processedNumbers = numbers.map(n => Number(n));
              
              // Comparar com os dados atuais para verificar se há novidades
              if (JSON.stringify(processedNumbers) !== JSON.stringify(lastNumbers)) {
                console.log(`[EVENTO][${roletaNome}] Novos dados disponíveis, atualizando silenciosamente`);
                setLastNumbers(processedNumbers);
              } else {
                console.log(`[EVENTO][${roletaNome}] Dados iguais, mantendo estado atual`);
              }
              
              // Atualizar estado persistente de qualquer forma
              persistentState[roletaNome] = {
                lastNumbers: processedNumbers,
                lastUpdated: Date.now(),
                hasLoaded: true
              };
            }
          })
          .catch(error => {
            console.error(`[ERRO][${roletaNome}] Erro ao atualizar dados:`, error);
          });
      }
    };
    
    // Registrar manipulador para o evento personalizado
    window.addEventListener('app:returned-to-page', handleReturnToPage);
    
    // Limpar quando o componente desmontar
    return () => {
      window.removeEventListener('app:returned-to-page', handleReturnToPage);
    };
  }, [roletaNome, lastNumbers]);

  // Função para atualizar apenas o último número, sem recarregar todo o componente
  const updateLastNumber = useCallback((novoNumero: number) => {
    if (!lastNumbers.includes(novoNumero)) {
      console.log(`[UPDATE][${roletaNome}] Atualizando apenas o último número: ${novoNumero}`);
      
      // Salvar o número anterior para referência
      if (lastNumbers.length > 0) {
        setPreviousLastNumber(lastNumbers[0]);
      }
      
      // Verificar estratégia para o novo número
      verificarEstrategia(novoNumero);
      
      // Atualizar o array de números
      const updatedNumbers = [novoNumero, ...lastNumbers.slice(0, 19)];
      
      // Atualizar estado persistente
      persistentState[roletaNome] = {
        lastNumbers: updatedNumbers,
        lastUpdated: Date.now(),
        hasLoaded: true
      };
      
      // Atualizar o estado
      setLastNumbers(updatedNumbers);
      
      // Notificar sobre o novo número (apenas se o documento estiver visível)
      if (isDocumentVisible()) {
        toast({
          title: "Novo Número",
          description: `${novoNumero} (${roletaNome})`,
          variant: "default",
        });
      }
      
      return true;
    }
    
    return false;
  }, [lastNumbers, roletaNome]);

  // Inicialização - Carrega dados apenas se necessário
  useEffect(() => {
    console.log(`[CICLO][${roletaNome}] Componente montado`);
    
    // Se os componentes estão congelados, não fazer nada além de carregar do estado persistente
    if (areComponentsFrozen()) {
      console.log(`[CICLO][${roletaNome}] Componentes congelados, usando apenas estado persistente`);
      
      if (persistentState[roletaNome]?.lastNumbers?.length > 0) {
        setLastNumbers(persistentState[roletaNome].lastNumbers);
        setIsLoading(false);
        setDataSeeded(true);
        return;
      }
    }
    
    const needsUpdate = () => {
      // Se estamos congelados, não atualizar
      if (areComponentsFrozen()) {
        return false;
      }
      
      // Se já temos estado persistente e foi atualizado recentemente, não precisamos atualizar
      if (persistentState[roletaNome]?.hasLoaded) {
        const lastUpdated = persistentState[roletaNome].lastUpdated;
        const now = Date.now();
        const fiveMinutes = 5 * 60 * 1000;
        
        // Se foi atualizado há menos de 5 minutos, não precisamos atualizar
        if (now - lastUpdated < fiveMinutes) {
          console.log(`[CICLO][${roletaNome}] Dados ainda recentes (${Math.round((now - lastUpdated)/1000)}s), pulando busca`);
          return false;
        }
      }
      
      // Se não estiver visível, não precisamos atualizar agora
      if (!isDocumentVisible()) {
        console.log(`[CICLO][${roletaNome}] Documento não visível, adiando atualização`);
        return false;
      }
      
      return true;
    };
    
    if (needsUpdate()) {
      // Buscar dados iniciais do Supabase
      console.log(`[CICLO][${roletaNome}] Buscando dados iniciais no Supabase...`);
      
      fetchRouletteLatestNumbersByName(roletaNome, 20)
        .then(numbers => {
          if (!isMounted.current) return;
          
          if (numbers && numbers.length > 0) {
            console.log(`[CICLO][${roletaNome}] Recebidos ${numbers.length} números`);
            const processedNumbers = numbers.map(n => Number(n));
            setLastNumbers(processedNumbers);
            setUsingSupabaseData(true);
            
            // Atualizar estado persistente
            persistentState[roletaNome] = {
              lastNumbers: processedNumbers,
              lastUpdated: Date.now(),
              hasLoaded: true
            };
          } else if (initialLastNumbers && initialLastNumbers.length > 0) {
            console.log(`[CICLO][${roletaNome}] Sem dados do Supabase, usando iniciais`);
            setLastNumbers(initialLastNumbers);
          }
          
          setIsLoading(false);
          setDataSeeded(true);
        })
        .catch(error => {
          if (!isMounted.current) return;
          
          console.error(`[ERRO][${roletaNome}] Erro ao buscar dados:`, error);
          if (initialLastNumbers && initialLastNumbers.length > 0) {
            setLastNumbers(initialLastNumbers);
          }
          setIsLoading(false);
          setDataSeeded(true);
        });
    } else {
      // Já temos dados recentes, apenas confirmar que está carregado
      setIsLoading(false);
      setDataSeeded(true);
    }
    
    // Configurar assinatura do Supabase Realtime para a tabela roleta_numeros
    let subscription: any = null;
    
    if (isDocumentVisible()) {
      try {
        console.log(`[REALTIME][${roletaNome}] Configurando canal Realtime...`);
        
        subscription = supabase
          .channel(`roleta_numeros_changes_${roletaNome}`)
          .on('postgres_changes', { 
            event: 'INSERT', 
            schema: 'public', 
            table: 'roleta_numeros',
            filter: `roleta_nome=eq.${roletaNome}`
          }, (payload) => {
            if (!isMounted.current) return;
            
            if (payload.new && payload.new.roleta_nome === roletaNome) {
              const novoNumero = Number(payload.new.numero);
              console.log(`[REALTIME][${roletaNome}] Novo número: ${novoNumero}`);
              
              // Usar a função updateLastNumber para atualizar apenas o último número
              updateLastNumber(novoNumero);
            }
          })
          .subscribe((status: string) => {
            console.log(`[REALTIME][${roletaNome}] Status da assinatura: ${status}`);
          });
          
        supabaseSubscriptionRef.current = subscription;
      } catch (error) {
        console.error(`[REALTIME][${roletaNome}] Erro ao configurar Realtime:`, error);
      }
    }
    
    // Registrar evento de visibilidade
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log(`[VISIBILIDADE][${roletaNome}] Documento visível, verificando estado`);
        
        // Verificar se precisamos atualizar dados
        const lastUpdated = persistentState[roletaNome]?.lastUpdated || 0;
        const now = Date.now();
        const tenMinutes = 10 * 60 * 1000;
        
        if (now - lastUpdated > tenMinutes) {
          console.log(`[VISIBILIDADE][${roletaNome}] Dados antigos, atualizando...`);
          
          fetchRouletteLatestNumbersByName(roletaNome, 1)
            .then(numbers => {
              if (!isMounted.current) return;
              
              if (numbers && numbers.length > 0) {
                const novoNumero = Number(numbers[0]);
                
                // Atualizar apenas o último número
                updateLastNumber(novoNumero);
              }
            })
            .catch(error => {
              console.error(`[ERRO][${roletaNome}] Erro ao atualizar dados:`, error);
            });
        }
        
        // Verificar se precisa recriar assinatura
        if (!subscription && !supabaseSubscriptionRef.current) {
          try {
            console.log(`[REALTIME][${roletaNome}] Recriando canal Realtime...`);
            
            subscription = supabase
              .channel(`roleta_numeros_changes_${roletaNome}`)
              .on('postgres_changes', { 
                event: 'INSERT', 
                schema: 'public', 
                table: 'roleta_numeros',
                filter: `roleta_nome=eq.${roletaNome}`
              }, (payload) => {
                // Lógica de processamento da mensagem
                if (payload.new && payload.new.roleta_nome === roletaNome) {
                  const novoNumero = Number(payload.new.numero);
                  // Lógica de atualização...
                }
              })
              .subscribe();
              
            supabaseSubscriptionRef.current = subscription;
          } catch (error) {
            console.error(`[REALTIME][${roletaNome}] Erro ao recriar Realtime:`, error);
          }
        }
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Limpeza
    return () => {
      console.log(`[CICLO][${roletaNome}] Componente desmontado`);
      isMounted.current = false;
      
      if (subscription) {
        console.log(`[REALTIME][${roletaNome}] Removendo assinatura`);
        supabase.removeChannel(subscription);
      }
      
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [roletaNome]); // Dependência apenas do nome da roleta

  const verificarEstrategia = (numero: number) => {
    // Placeholder para verificação de estratégia
    console.log(`[${roletaNome}] Verificando estratégia para número: ${numero}`);
  };

  useEffect(() => {
    generateSuggestion();
  }, []);

  const generateSuggestion = () => {
    const groupKeys = Object.keys(numberGroups);
    const randomGroupKey = groupKeys[Math.floor(Math.random() * groupKeys.length)];
    const selectedGroup = numberGroups[randomGroupKey as keyof typeof numberGroups];
    
    const relatedStrategy = strategies.find(s => s.name.includes(selectedGroup.numbers.join(',')));
    setCurrentStrategy(relatedStrategy || strategies[0]);
    
    setSuggestion([...selectedGroup.numbers]);
    setSelectedGroup(randomGroupKey);
    
    toast({
      title: "Sugestão Gerada",
      description: `Grupo: ${selectedGroup.name}`,
      variant: "default"
    });
  };

  const toggleVisibility = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsBlurred(!isBlurred);
  };

  const handleDetailsClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setStatsOpen(true);
  };

  const handlePlayClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    toast({
      title: "Roleta Aberta",
      description: "Redirecionando para o jogo...",
      variant: "default"
    });
  };

  // Atualizando o memoizedNumbers para evitar qualquer piscar durante a atualização
  const memoizedNumbers = useMemo(() => {
    // Apenas renderizar quando realmente temos dados, nunca estados vazios
    const numbersToShow = lastNumbers.length > 0 ? 
      lastNumbers : 
      (persistentState[roletaNome]?.lastNumbers || initialLastNumbers || []);
      
    return (
      <LastNumbers 
        numbers={numbersToShow} 
        isLoading={false} // Nunca mostrar estado de carregamento
      />
    );
  }, [lastNumbers, isLoading, roletaNome, initialLastNumbers]);

  const memoizedSuggestion = useMemo(() => (
    <SuggestionDisplay 
      suggestion={suggestion}
      selectedGroup={selectedGroup}
      isBlurred={isBlurred}
      toggleVisibility={toggleVisibility}
      numberGroups={numberGroups}
    />
  ), [suggestion, selectedGroup, isBlurred]);

  const memoizedWinRate = useMemo(() => (
    <WinRateDisplay wins={wins} losses={losses} />
  ), [wins, losses]);

  const memoizedTrendChart = useMemo(() => (
    <RouletteTrendChart trend={trend} />
  ), [trend]);

  const memoizedActionButtons = useMemo(() => (
    <RouletteActionButtons 
      onDetailsClick={handleDetailsClick}
      onPlayClick={handlePlayClick}
    />
  ), []);

  // Função para determinar a cor do número da roleta
  const getRouletteNumberColor = (num: number) => {
    num = Number(num); // Garantir que o número está no formato correto
    if (num === 0) {
      return 'bg-green-600 text-white'; // Verde para o zero
    } else if ([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36].includes(num)) {
      return 'bg-red-600 text-white'; // Vermelho para números específicos
    } else {
      return 'bg-black text-white'; // Preto para os demais números
    }
  };

  return (
    <div 
      className="bg-card rounded-lg shadow-lg p-4 relative overflow-hidden"
      data-roulette-name={roletaNome}
    >
      <div className="absolute inset-0 bg-gradient-to-b from-black/30 to-transparent z-0"></div>
      
      <div className="relative z-10 space-y-2">
        {/* Cabeçalho */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <h3 className="text-xl font-bold">{roletaNome}</h3>
            <div className="flex gap-1">
              {showSuggestions && <SuggestionDisplay 
                suggestion={suggestion}
                selectedGroup={selectedGroup}
                isBlurred={isBlurred}
                toggleVisibility={toggleVisibility}
                numberGroups={numberGroups}
              />}
            </div>
          </div>
          
          <div className="flex items-center gap-2">
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleDetailsClick}
              className="relative">
              <ChartBar className="w-4 h-4" />
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handlePlayClick}
              className="relative bg-blue-500 hover:bg-blue-600">
              Play
            </Button>
          </div>
        </div>
        
        {/* Números - o componente que não deve piscar */}
        <div className="no-flash-container">
          {memoizedNumbers}
        </div>
        
        {/* Taxa de vitórias */}
        <WinRateDisplay 
          wins={wins}
          losses={losses}
        />
        
        {/* Tendência */}
        <RouletteTrendChart data={trend} />
        
        {/* Botões de ação */}
        <RouletteActionButtons onSuggestionClick={generateSuggestion} />
      </div>
      
      {/* Modal de estatísticas */}
      <RouletteStatsModal
        open={statsOpen}
        onOpenChange={setStatsOpen}
        rouletteName={roletaNome}
        numbers={lastNumbers}
        wins={wins}
        losses={losses}
      />
    </div>
  );
};

// Funções auxiliares para insights
const getColorName = (num: number): string => {
  num = Number(num); // Garantir que o número está no formato correto
  if (num === 0) return "Verde";
  if ([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36].includes(num)) return "Vermelho";
  return "Preto";
};

const getColorStreak = (numbers: number[]): number => {
  const firstColor = getColorName(numbers[0]);
  let streak = 1;
  
  for (let i = 1; i < numbers.length; i++) {
    if (getColorName(numbers[i]) === firstColor) {
      streak++;
    } else {
      break;
    }
  }
  
  return streak;
};

const getInsightMessage = (numbers: number[], wins: number, losses: number): string => {
  const lastNum = numbers[0];
  const isRed = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36].includes(lastNum);
  const isBlack = lastNum !== 0 && !isRed;
  const winRate = wins / (wins + losses);
  
  if (winRate > 0.65) {
    return "Momento favorável para apostar em números " + (isRed ? "pretos" : "vermelhos");
  } else if (numbers.filter(n => n % 2 === 0).length > numbers.length * 0.7) {
    return "Tendência de números pares nas últimas rodadas";
  } else if (numbers.filter(n => n % 2 !== 0).length > numbers.length * 0.7) {
    return "Tendência de números ímpares nas últimas rodadas";
  } else if (numbers.filter(n => n <= 18).length > numbers.length * 0.7) {
    return "Tendência de números baixos (1-18) nas últimas rodadas";
  } else if (numbers.filter(n => n > 18 && n <= 36).length > numbers.length * 0.7) {
    return "Tendência de números altos (19-36) nas últimas rodadas";
  } else {
    return "Distribua suas apostas em diferentes setores da mesa";
  }
};

export default RouletteCard;
