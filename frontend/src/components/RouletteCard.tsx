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
import EventService, { RouletteNumberEvent } from '@/services/EventService';

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
  
  // Referência ao serviço de eventos
  const eventServiceRef = useRef<EventService | null>(null);

  useEffect(() => {
    console.log(`[DEPURAÇÃO][${name}] Inicializando componente RouletteCard`);
    
    // Inicializar o serviço de eventos
    const eventService = EventService.getInstance();
    eventServiceRef.current = eventService;
    
    const checkAndSeedData = async () => {
      try {
        console.log(`[DEPURAÇÃO][${name}] Buscando dados iniciais no Supabase...`);
        setIsLoading(true);
        
        // Buscar números iniciais do Supabase
        console.log(`[DEPURAÇÃO][${name}] Chamando fetchRouletteLatestNumbersByName...`);
        const numbers = await fetchRouletteLatestNumbersByName(name, 20);
        
        console.log(`[DEPURAÇÃO][${name}] Números recebidos:`, numbers);
        
        if (numbers && numbers.length > 0) {
          console.log(`[DEPURAÇÃO][${name}] ${numbers.length} números encontrados:`, numbers);
          setLastNumbers(numbers);
          setUsingSupabaseData(true);
          setDataSeeded(true);
          
          toast({
            title: `Dados carregados: ${name}`,
            description: `${numbers.length} números encontrados: ${numbers.slice(0, 3).join(', ')}...`,
            variant: 'default',
          });
        } else {
          console.log(`[DEPURAÇÃO][${name}] Nenhum número encontrado no Supabase`);
          
          // Usar os dados iniciais como fallback apenas se realmente não houver dados no Supabase
          if (initialLastNumbers && initialLastNumbers.length > 0) {
            console.log(`[DEPURAÇÃO][${name}] Usando dados iniciais:`, initialLastNumbers);
            setLastNumbers(initialLastNumbers);
          } else {
            console.log(`[DEPURAÇÃO][${name}] Nenhum dado inicial disponível. Usando array vazio.`);
            setLastNumbers([]);
          }
          
          setUsingSupabaseData(false);
          setDataSeeded(true);
          
          toast({
            title: `Sem dados: ${name}`,
            description: 'Nenhum número encontrado no Supabase',
            variant: 'destructive',
          });
        }
      } catch (error) {
        console.error(`[ERRO][${name}] Erro ao buscar dados:`, error);
        
        // Usar os dados iniciais como fallback em caso de erro
        if (initialLastNumbers && initialLastNumbers.length > 0) {
          setLastNumbers(initialLastNumbers);
        }
        
        setUsingSupabaseData(false);
        setDataSeeded(true);
        
        toast({
          title: `Erro: ${name}`,
          description: `Erro ao buscar dados: ${error}`,
          variant: 'destructive',
        });
      } finally {
        setIsLoading(false);
      }
    };

    checkAndSeedData();
  }, [name, initialLastNumbers]);

  // Handler para novos eventos de números de roleta
  const handleNewNumber = useCallback((event: RouletteNumberEvent) => {
    console.log(`[SSE][${name}] Novo número recebido via SSE: ${event.numero}`);
    
    if (event.roleta_nome !== name) {
      console.log(`[SSE][${name}] Ignorando evento para outra roleta: ${event.roleta_nome}`);
      return; // Ignorar eventos para outras roletas
    }
    
    // Atualizar o estado apenas se for um número novo
    setLastNumbers(currentNumbers => {
      // Verificar se o número é realmente novo
      const isNewNumber = currentNumbers.length === 0 || currentNumbers[0] !== event.numero;
      console.log(`[SSE][${name}] É número novo? ${isNewNumber}. Atual: ${currentNumbers[0]}, Novo: ${event.numero}`);
      
      if (isNewNumber) {
        // Salvar o número anterior
        if (currentNumbers.length > 0) {
          setPreviousLastNumber(currentNumbers[0]);
        }
        
        // Verificar estratégia para o novo número
        verificarEstrategia(event.numero);
        
        // Criar o novo array de números
        const updatedNumbers = [event.numero, ...currentNumbers.slice(0, 19)];
        console.log(`[SSE][${name}] Atualizando números: ${updatedNumbers.slice(0, 5).join(', ')}...`);
        
        toast({
          title: "Novo Número",
          description: `${event.numero} (${name})`,
          variant: "default",
        });
        
        return updatedNumbers;
      }
      
      return currentNumbers;
    });
  }, [name]);

  // Inscrever-se para receber eventos da roleta específica
  useEffect(() => {
    if (dataSeeded && eventServiceRef.current) {
      console.log(`[SSE][${name}] Inscrevendo para eventos da roleta: ${name}`);
      
      // Inscrever-se para receber atualizações de qualquer roleta (*) para fins de depuração
      console.log(`[SSE][${name}] TAMBÉM inscrevendo para todos os eventos (*) para depuração`);
      eventServiceRef.current.subscribe('*', (event) => {
        console.log(`[SSE][GLOBAL] Evento recebido para ${event.roleta_nome}: ${event.numero}`);
      });
      
      // Inscrever-se para receber atualizações em tempo real desta roleta específica
      eventServiceRef.current.subscribe(name, handleNewNumber);
      
      // Limpar inscrição quando o componente desmontar
      return () => {
        if (eventServiceRef.current) {
          console.log(`[SSE][${name}] Cancelando inscrição de eventos`);
          eventServiceRef.current.unsubscribe('*', () => {});
          eventServiceRef.current.unsubscribe(name, handleNewNumber);
        }
      };
    }
  }, [dataSeeded, name, handleNewNumber]);

  const verificarEstrategia = (numero: number) => {
    // Placeholder para verificação de estratégia
    console.log(`[${name}] Verificando estratégia para número: ${numero}`);
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
        <h3 className="text-lg font-semibold">{name}</h3>
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
          <h2 className="text-lg font-semibold text-[#00ff00]">{name}</h2>
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
        name={name}
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
