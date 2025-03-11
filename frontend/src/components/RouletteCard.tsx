import { TrendingUp, ChartBar, ArrowUp, ArrowDown, Eye, EyeOff, BarChart3, PlayCircle, PieChart, History, Clock, Target, Percent, Heart, Star, AlertTriangle, BarChart } from 'lucide-react';
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
import { useRoletaAnalytics } from '@/hooks/useRoletaAnalytics';

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
      const thirtyMinutes = 30 * 60 * 1000;
      
      // Só atualizar se ficar mais de 30 minutos fora
      if (event.detail.timeAway > thirtyMinutes) {
        console.log(`[EVENTO][${roletaNome}] Tempo fora maior que 30 minutos, atualizando dados`);
    
        // Atualização silenciosa em segundo plano, sem alterar UI imediatamente
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
            filter: 'roleta_nome=eq.' + roletaNome
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
        
        // Aumentar o intervalo para 30 minutos em vez de 10 minutos para reduzir recargas
        const thirtyMinutes = 30 * 60 * 1000;
        
        // Verificar se o sistema está congelado (bloqueio anti-recarga)
        if (areComponentsFrozen()) {
          console.log(`[VISIBILIDADE][${roletaNome}] Componentes congelados, mantendo estado atual`);
          return;
        }
        
        // Só atualizar se os dados forem muito antigos
        if (now - lastUpdated > thirtyMinutes) {
          console.log(`[VISIBILIDADE][${roletaNome}] Dados antigos, atualizando...`);
          
          fetchRouletteLatestNumbersByName(roletaNome, 1)
            .then(numbers => {
              if (!isMounted.current) return;
              
              if (numbers && numbers.length > 0) {
                const novoNumero = Number(numbers[0]);
                
                // Comparar com o número atual antes de atualizar
                if (lastNumbers.length === 0 || lastNumbers[0] !== novoNumero) {
                  // Atualizar apenas o último número
                  updateLastNumber(novoNumero);
                } else {
                  console.log(`[VISIBILIDADE][${roletaNome}] Mesmo número, não atualizando UI`);
                  // Apenas atualizar o timestamp sem recarregar a UI
                  persistentState[roletaNome] = {
                    ...(persistentState[roletaNome] || {}),
                    lastNumbers: lastNumbers,  // Garantir que lastNumbers está presente
                    lastUpdated: now,
                    hasLoaded: true
                  };
                }
              }
            })
            .catch(error => {
              console.error(`[ERRO][${roletaNome}] Erro ao atualizar dados:`, error);
            });
        } else {
          console.log(`[VISIBILIDADE][${roletaNome}] Dados recentes (${Math.round((now - lastUpdated)/1000)}s), mantendo estado`);
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

  // Adicionar uso do hook useRoletaAnalytics para estatísticas simplificadas
  const { 
    colorDistribution, 
    currentStreak,
    missingDozens,
    loading: analyticsLoading 
  } = useRoletaAnalytics(roletaNome, 30000); // Atualiza a cada 30 segundos

  return (
    <div 
      className="bg-[#17161e]/90 backdrop-filter backdrop-blur-sm border border-white/10 rounded-xl p-3 md:p-4 space-y-2 md:space-y-3 animate-fade-in hover-scale cursor-pointer h-auto w-full overflow-hidden"
      onClick={handleDetailsClick}
    >
      <div className="flex items-center justify-end">
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
      
      {/* Insights Section - Versão redesenhada e simplificada */}
      <div className="p-3 bg-[#1a1922] rounded-lg border border-[#00ff00]/20">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-sm font-medium text-white flex items-center">
            <BarChart3 size={16} className="text-[#00ff00] mr-1.5" />
            Análises Rápidas
          </h4>
          {!analyticsLoading && (
            <span className="text-xs text-gray-400 bg-[#252431] px-2 py-0.5 rounded-full">
              {lastNumbers.length} jogadas
            </span>
          )}
        </div>
        
        <div className="grid grid-cols-2 gap-2 mb-3">
          {/* Mini-card 1: Distribuição de cores */}
          <div className="p-2 bg-[#252431] rounded-lg">
            <div className="flex items-center mb-1.5">
              <PieChart size={14} className="text-[#00ff00] mr-1" />
              <span className="text-[10px] uppercase font-medium text-gray-400">Cores</span>
            </div>
            
            {!analyticsLoading && colorDistribution.length > 0 ? (
              <div className="flex space-x-1">
                {colorDistribution.map((item, idx) => (
                  <div 
                    key={idx} 
                    className="flex-1 h-5 rounded-sm flex items-center justify-center"
                    style={{
                      backgroundColor: item.cor === 'vermelho' ? '#ef4444' : 
                                      item.cor === 'preto' ? '#1e1e1e' : '#10b981',
                      opacity: 0.7 + (item.porcentagem / 100) * 0.3
                    }}
                  >
                    <span className="text-[10px] font-bold text-white">
                      {Math.round(item.porcentagem)}%
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-5 bg-gray-700/30 rounded-sm animate-pulse"></div>
            )}
          </div>
          
          {/* Mini-card 2: Taxa de Acerto */}
          <div className="p-2 bg-[#252431] rounded-lg">
            <div className="flex items-center mb-1.5">
              <Target size={14} className="text-[#00ff00] mr-1" />
              <span className="text-[10px] uppercase font-medium text-gray-400">Acertos</span>
            </div>
            
            <div className="flex items-center space-x-2">
              <div 
                className="flex-1 h-5 bg-gray-700/30 rounded-sm overflow-hidden"
              >
                <div 
                  className="h-full bg-gradient-to-r from-blue-500 to-[#00ff00]"
                  style={{ width: `${Math.min(100, Math.max(1, ((wins / (wins + losses)) * 100)))}%` }}
                ></div>
              </div>
              <span className="text-sm font-bold text-[#00ff00]">
                {((wins / (wins + losses)) * 100).toFixed(0)}%
              </span>
            </div>
          </div>
        </div>
        
        <div className="grid grid-cols-3 gap-2 mb-3">
          {/* Célula 1: Sequência Atual */}
          <div className="bg-[#252431] p-2 rounded-lg flex flex-col justify-between">
            <div className="flex items-center mb-1">
              <History size={14} className="text-purple-400 mr-1.5" />
              <span className="text-[10px] uppercase font-medium text-gray-400">Sequência</span>
            </div>
            <div className="text-right">
              <span className="text-xs font-medium text-purple-400">
                {!analyticsLoading && currentStreak.count > 0 
                  ? `${currentStreak.count}x ${currentStreak.value}`
                  : "---"}
              </span>
            </div>
          </div>
          
          {/* Célula 2: Dúzia Ausente */}
          <div className="bg-[#252431] p-2 rounded-lg flex flex-col justify-between">
            <div className="flex items-center mb-1">
              <Clock size={14} className="text-yellow-400 mr-1.5" />
              <span className="text-[10px] uppercase font-medium text-gray-400">Dúzia</span>
            </div>
            <div className="text-right">
              <span className="text-xs font-medium text-yellow-400">
                {!analyticsLoading && missingDozens.length > 0
                  ? `${missingDozens[0].dezena} (${missingDozens[0].ausencia}x)`
                  : "---"}
              </span>
            </div>
          </div>
          
          {/* Célula 3: Recomendação */}
          <div className="bg-[#252431] p-2 rounded-lg flex flex-col justify-between">
            <div className="flex items-center mb-1">
              <Star size={14} className="text-[#00ff00] mr-1.5" />
              <span className="text-[10px] uppercase font-medium text-gray-400">Recomendação</span>
            </div>
            <div className="text-right">
              <span className="text-xs font-medium text-[#00ff00]">
                {getColorName(lastNumbers[0] || 0).toUpperCase()}
              </span>
            </div>
          </div>
        </div>
        
        {/* Botão "Ver Análise Completa" removido a pedido do usuário */}
      </div>
      
      {memoizedActionButtons}

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
