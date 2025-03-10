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

const RouletteCard = ({ name, lastNumbers: initialLastNumbers, wins, losses, trend }: RouletteCardProps) => {
  const navigate = useNavigate();
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [suggestion, setSuggestion] = useState<number[]>([]);
  const [isBlurred, setIsBlurred] = useState(false);
  const [currentStrategy, setCurrentStrategy] = useState(strategies[0]);
  const [selectedGroup, setSelectedGroup] = useState<string>("grupo-123");
  const [lastNumbers, setLastNumbers] = useState<number[]>([]);
  const [previousLastNumber, setPreviousLastNumber] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [dataSeeded, setDataSeeded] = useState(false);
  const [statsOpen, setStatsOpen] = useState(false);
  const [usingSupabaseData, setUsingSupabaseData] = useState(false);
  const [isInitialRender, setIsInitialRender] = useState(true);
  
  // Referência para o intervalo de polling (desativado por padrão)
  const pollingIntervalRef = useRef<number | null>(null);
  
  // Referência para a assinatura do Supabase Realtime
  const supabaseSubscriptionRef = useRef<any>(null);
  
  // Controle para ativar/desativar o polling
  const ENABLE_POLLING = false; // Desativado por padrão
  const POLLING_INTERVAL = 15000; // 15 segundos

  // Verificar se o nome da roleta é válido
  const roletaNome = name || "Roleta Desconhecida";
  
  // Reduzindo logs para evitar poluição do console
  if (isInitialRender) {
    console.log(`[DEPURAÇÃO][${roletaNome}] Renderizando card com dados:`, { 
      name: roletaNome, 
      initialNumbersLength: initialLastNumbers?.length || 0,
      wins, 
      losses 
    });
  }

  // Função para verificar se a página está visível
  const isDocumentVisible = () => document.visibilityState === 'visible';

  useEffect(() => {
    // Marcar que não é mais a renderização inicial
    setIsInitialRender(false);
    
    // Verificar se já há um timestamp de carregamento
    const componentLoadedTimestamp = localStorage.getItem(`roulette_${roletaNome}_loaded_timestamp`);
    const currentTime = Date.now();
    const cacheExpiration = 5 * 60 * 1000; // 5 minutos
    
    // Se os dados foram carregados recentemente, usar os dados em cache
    if (componentLoadedTimestamp && 
        currentTime - parseInt(componentLoadedTimestamp) < cacheExpiration && 
        initialLastNumbers && initialLastNumbers.length > 0) {
      console.log(`[CACHE][${roletaNome}] Usando dados em cache`);
      setLastNumbers(initialLastNumbers);
      setDataSeeded(true);
      setIsLoading(false);
      return;
    }
    
    // Se estiver voltando para a página e não for visível, não recarregar dados
    if (!isInitialRender && !isDocumentVisible()) {
      console.log(`[OTIMIZAÇÃO][${roletaNome}] Página não visível, não recarregando dados`);
      setLastNumbers(lastNumbers.length > 0 ? lastNumbers : initialLastNumbers || []);
      setDataSeeded(true);
      setIsLoading(false);
      return;
    }
    
    console.log(`[DEPURAÇÃO][${roletaNome}] Inicializando componente RouletteCard`);
    
    const checkAndSeedData = async () => {
      try {
        console.log(`[DEPURAÇÃO][${roletaNome}] Buscando dados iniciais no Supabase...`);
        setIsLoading(true);
        
        // Buscar números iniciais do Supabase
        console.log(`[DEPURAÇÃO][${roletaNome}] Chamando fetchRouletteLatestNumbersByName...`);
        const numbers = await fetchRouletteLatestNumbersByName(roletaNome, 20);
        
        console.log(`[DEPURAÇÃO][${roletaNome}] Números recebidos:`, numbers);
        
        if (numbers && numbers.length > 0) {
          setLastNumbers(numbers.map(n => Number(n)));
          setDataSeeded(true);
          setUsingSupabaseData(true);
          setIsLoading(false);
          
          // Salvar timestamp para controle de cache
          localStorage.setItem(`roulette_${roletaNome}_loaded_timestamp`, Date.now().toString());
          
          console.log(`[DEPURAÇÃO][${roletaNome}] Dados carregados com sucesso do Supabase`);
        } else {
          console.log(`[DEPURAÇÃO][${roletaNome}] Nenhum dado encontrado no Supabase, usando dados iniciais`);
          setLastNumbers(initialLastNumbers || []);
          setDataSeeded(true);
          setUsingSupabaseData(false);
          setIsLoading(false);
        }
      } catch (error) {
        console.error(`[ERRO][${roletaNome}] Erro ao buscar dados:`, error);
        setLastNumbers(initialLastNumbers || []);
        setDataSeeded(true);
        setUsingSupabaseData(false);
        setIsLoading(false);
      }
    };

    // Verificar se já temos dados iniciais antes de buscar no Supabase
    if (initialLastNumbers && initialLastNumbers.length > 0) {
      setLastNumbers(initialLastNumbers);
      setDataSeeded(true);
      setIsLoading(false);
      
      // Ainda assim, atualizar em segundo plano para dados mais recentes
      checkAndSeedData();
    } else {
      checkAndSeedData();
    }
    
    // Configurar polling como fallback (desativado por padrão)
    const startPolling = () => {
      // Verificar se o polling está habilitado
      if (!ENABLE_POLLING) {
        console.log(`[POLLING][${roletaNome}] Polling desativado por configuração`);
        return;
      }
      
      console.log(`[POLLING][${roletaNome}] Iniciando polling como fallback para SSE`);
      
      // Limpar intervalo anterior se existir
      if (pollingIntervalRef.current) {
        window.clearInterval(pollingIntervalRef.current);
      }
      
      // Criar novo intervalo de polling
      pollingIntervalRef.current = window.setInterval(async () => {
        try {
          console.log(`[POLLING][${roletaNome}] Verificando novos números...`);
          const latestNumbers = await fetchRouletteLatestNumbersByName(roletaNome, 1);
          
          if (latestNumbers && latestNumbers.length > 0) {
            const latestNumber = Number(latestNumbers[0]);
            
            // Comparar com o número atual
            setLastNumbers(currentNumbers => {
              if (currentNumbers.length === 0 || currentNumbers[0] !== latestNumber) {
                console.log(`[POLLING][${roletaNome}] Novo número encontrado via polling: ${latestNumber}`);
                
                // Salvar o número anterior
                if (currentNumbers.length > 0) {
                  setPreviousLastNumber(currentNumbers[0]);
                }
                
                // Verificar estratégia para o novo número
                verificarEstrategia(latestNumber);
                
                // Criar o novo array de números
                const updatedNumbers = [latestNumber, ...currentNumbers.slice(0, 19)];
                
                toast({
                  title: "Novo Número (via Polling)",
                  description: `${latestNumber} (${roletaNome})`,
                  variant: "default",
                });
                
                return updatedNumbers;
              }
              return currentNumbers;
            });
          }
        } catch (error) {
          console.error(`[POLLING][${roletaNome}] Erro ao buscar novos números:`, error);
        }
      }, POLLING_INTERVAL);
    };
    
    // Iniciar polling se estiver habilitado
    startPolling();
    
    // Modificação para controlar assinaturas Realtime com base na visibilidade da página
    let subscription: any = null;
    
    // Função para configurar a assinatura Realtime
    const setupRealtimeSubscription = () => {
      // Apenas configurar se o documento estiver visível
      if (!isDocumentVisible()) {
        console.log(`[REALTIME][${roletaNome}] Documento não visível, adiando assinatura Realtime`);
        return null;
      }
      
      console.log(`[REALTIME][${roletaNome}] Configurando assinatura do Supabase Realtime...`);
      
      try {
        // Inscrever-se para atualizações na tabela roleta_numeros
        console.log(`[REALTIME][${roletaNome}] Criando canal Realtime para roleta_numeros...`);
        
        const channel = supabase
          .channel(`roleta_numeros_changes_${roletaNome}`)
          .on('postgres_changes', { 
            event: 'INSERT', 
            schema: 'public', 
            table: 'roleta_numeros',
            filter: `roleta_nome=eq.${roletaNome}`
          }, (payload) => {
            console.log(`[REALTIME][${roletaNome}] Evento do Supabase recebido:`, payload);
            
            // Verificar se o novo número é para esta roleta
            if (payload.new && payload.new.roleta_nome === roletaNome) {
              const novoNumero = Number(payload.new.numero);
              console.log(`[REALTIME][${roletaNome}] Novo número para esta roleta: ${novoNumero}`);
              
              // Atualizar o estado com o novo número
              setLastNumbers(currentNumbers => {
                // Verificar se é um número novo
                if (currentNumbers.length === 0 || currentNumbers[0] !== novoNumero) {
                  console.log(`[REALTIME][${roletaNome}] Atualizando números com: ${novoNumero}`);
                  
                  // Salvar o número anterior
                  if (currentNumbers.length > 0) {
                    setPreviousLastNumber(currentNumbers[0]);
                  }
                  
                  // Verificar estratégia para o novo número
                  verificarEstrategia(novoNumero);
                  
                  // Exibir notificação toast apenas se o documento estiver visível
                  if (isDocumentVisible()) {
                    toast({
                      title: "Novo Número (Realtime)",
                      description: `${novoNumero} (${roletaNome})`,
                      variant: "default",
                    });
                  }
                  
                  return [novoNumero, ...currentNumbers.slice(0, 19)];
                }
                return currentNumbers;
              });
            }
          })
          .subscribe((status: string) => {
            console.log(`[REALTIME][${roletaNome}] Status da assinatura Realtime:`, status);
          });
          
        return channel;
      } catch (error) {
        console.error(`[REALTIME][${roletaNome}] Erro ao configurar Supabase Realtime:`, error);
        return null;
      }
    };
    
    // Configurar assinatura inicial
    subscription = setupRealtimeSubscription();
    supabaseSubscriptionRef.current = subscription;
    
    // Configurar listener para visibilidade do documento
    const handleVisibilityChange = () => {
      console.log(`[VISIBILIDADE][${roletaNome}] Estado de visibilidade mudou para:`, document.visibilityState);
      
      if (document.visibilityState === 'visible') {
        // Se o documento se tornou visível e não há assinatura ativa, configurar uma nova
        if (!supabaseSubscriptionRef.current) {
          console.log(`[REALTIME][${roletaNome}] Documento visível novamente, reativando assinatura Realtime`);
          subscription = setupRealtimeSubscription();
          supabaseSubscriptionRef.current = subscription;
        }
      } else {
        // Se o documento não está mais visível, considerar remover a assinatura para economizar recursos
        // Por enquanto, mantemos a assinatura para garantir atualização rápida quando voltar
      }
    };
    
    // Adicionar listener de visibilidade
    document.addEventListener('visibilitychange', handleVisibilityChange);
    
    // Limpar quando o componente desmontar
    return () => {
      console.log(`[CLEANUP][${roletaNome}] Limpando assinaturas e listeners`);
      
      // Remover assinatura do Supabase
      if (subscription) {
        console.log(`[REALTIME][${roletaNome}] Removendo assinatura Supabase`);
        supabase.removeChannel(subscription);
      }
      
      // Remover listener de visibilidade
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [roletaNome]);

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

  // Memorize components to prevent unnecessary re-renders
  const memoizedNumbers = useMemo(() => (
    <LastNumbers numbers={lastNumbers} isLoading={isLoading} />
  ), [lastNumbers, isLoading]);

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
      className="bg-[#17161e]/90 backdrop-filter backdrop-blur-sm border border-white/10 rounded-xl p-4 space-y-3 animate-fade-in hover-scale cursor-pointer h-auto"
      onClick={handleDetailsClick}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{roletaNome}</h3>
        <div className="flex items-center">
          {usingSupabaseData ? (
            <span className="text-xs mr-2 text-[#00ff00]">Dados do Supabase</span>
          ) : (
            <span className="text-xs mr-2 text-yellow-400">Aguardando Supabase</span>
          )}
          <TrendingUp size={20} className="text-[#00ff00]" />
        </div>
      </div>
      
      {memoizedNumbers}
      {memoizedSuggestion}
      {memoizedWinRate}
      {memoizedTrendChart}
      
      {/* Insights Section */}
      <div className="p-2 bg-[#1a1922] rounded-lg border border-[#00ff00]/20">
        <h4 className="text-xs font-medium text-[#00ff00] mb-1.5 flex items-center">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00ff00] mr-1.5"></span>
          Insights
        </h4>
        <div className="space-y-1.5">
          {lastNumbers.length > 0 && (
            <>
              {/* Tendência de cores */}
              <div className="flex items-center text-xs">
                <div className={`w-3 h-3 rounded-full mr-1.5 ${getRouletteNumberColor(lastNumbers[0]).replace('text-white', '')}`}></div>
                <span className="text-gray-300">
                  {getColorName(lastNumbers[0])} apareceu nas últimas {getColorStreak(lastNumbers)} rodadas
                </span>
              </div>
              
              {/* Dica de aposta */}
              <div className="flex items-center text-xs">
                <div className="w-3 h-3 rounded-full bg-[#00ff00] mr-1.5"></div>
                <span className="text-gray-300">
                  {getInsightMessage(lastNumbers, wins, losses)}
                </span>
              </div>
              
              {/* Estatística da sessão */}
              <div className="flex items-center text-xs">
                <div className="w-3 h-3 rounded-full bg-blue-500 mr-1.5"></div>
                <span className="text-gray-300">
                  Taxa de acerto: {((wins / (wins + losses)) * 100).toFixed(1)}% nos últimos 20 números
                </span>
              </div>
            </>
          )}
        </div>
      </div>
      
      {memoizedActionButtons}

      <div className="pt-2 flex flex-col h-full">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-[#00ff00]">{roletaNome}</h2>
          <Button
            variant="outline"
            size="sm"
            className="px-2 py-1 h-8 text-xs border-[#00ff00] text-[#00ff00] hover:bg-[#00ff00]/10"
            onClick={(e) => {
              e.stopPropagation();
              setStatsOpen(true);
            }}
          >
            <ChartBar className="h-3 w-3 mr-1" />
            Estatísticas
          </Button>
        </div>
        
        <div className="my-2">
          <h3 className="text-white/70 text-xs mb-1">Últimos números:</h3>
          <div className="flex flex-wrap gap-1">
            {lastNumbers.slice(0, 5).map((num, idx) => (
              <div
                key={`number-${idx}`}
                className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${getRouletteNumberColor(num)}`}
              >
                {num}
              </div>
            ))}
          </div>
        </div>
      </div>

      <RouletteStatsModal
        open={statsOpen}
        onOpenChange={setStatsOpen}
        name={roletaNome}
        lastNumbers={lastNumbers}
        wins={wins}
        losses={losses}
        trend={trend}
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
