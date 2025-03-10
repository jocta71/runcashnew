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
    console.log(`[DEPURAÇÃO][${name}] Novo número recebido via SSE: ${event.numero}`);
    
    // Atualizar o estado apenas se for uma roleta relevante
    if (event.roleta_nome === name || name.includes(event.roleta_nome)) {
      setLastNumbers(currentNumbers => {
        // Ignorar duplicações
        if (currentNumbers.length > 0 && currentNumbers[0] === event.numero) {
          return currentNumbers;
        }
        
        // Salvar o número anterior
        if (currentNumbers.length > 0) {
          setPreviousLastNumber(currentNumbers[0]);
        }
        
        // Verificar estratégia para o novo número
        verificarEstrategia(event.numero);
        
        // Criar o novo array de números
        const updatedNumbers = [event.numero, ...currentNumbers.slice(0, 19)];
        
        toast({
          title: "Novo Número",
          description: `${event.numero} (${name})`,
          variant: "default",
        });
        
        return updatedNumbers;
      });
    }
  }, [name]);

  // Inscrever-se para receber eventos da roleta específica
  useEffect(() => {
    if (dataSeeded && eventServiceRef.current) {
      console.log(`[DEPURAÇÃO][${name}] Inscrevendo para eventos da roleta`);
      
      // Inscrever-se para receber atualizações em tempo real
      eventServiceRef.current.subscribe(name, handleNewNumber);
      
      // Limpar inscrição quando o componente desmontar
      return () => {
        if (eventServiceRef.current) {
          console.log(`[DEPURAÇÃO][${name}] Cancelando inscrição de eventos`);
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

  const getRouletteNumberColor = (num: number) => {
    // Vermelho: 1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36
    const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
    if (num === 0) return 'bg-green-600'; // Verde para 0
    return redNumbers.includes(num) ? 'bg-red-600' : 'bg-black'; // Vermelho ou preto
  };

  return (
    <div className="bg-[#1A191F] rounded-xl overflow-hidden shadow-lg hover:shadow-xl transition-shadow duration-300 relative">
      <div 
        className="w-full h-full cursor-pointer" 
        onClick={() => navigate(`/roleta/${name.toLowerCase().replace(/\s+/g, '-')}`)}
      >
        <div className="p-4 border-b border-gray-800">
          <div className="flex justify-between items-center mb-2">
            <h3 className="text-lg font-bold text-white">{name}</h3>
            <span className="text-xs font-medium px-2 py-1 rounded-full bg-green-600 text-white">
              Ativo
            </span>
          </div>
          
          {usingSupabaseData ? (
            <div className="bg-green-900/20 border border-green-500/30 rounded-md px-2 py-1 text-xs text-green-400 mb-2">
              Dados em tempo real
            </div>
          ) : (
            <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-md px-2 py-1 text-xs text-yellow-400 mb-2">
              Dados de exemplo
            </div>
          )}
          
          {memoizedNumbers}
        </div>
        
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-start justify-between mb-2">
            <h4 className="text-md font-semibold text-white">Sugestão</h4>
            <button onClick={(e) => {e.stopPropagation(); generateSuggestion();}} className="text-xs text-vegas-gold hover:text-vegas-gold/80">
              Atualizar
            </button>
          </div>
          
          {memoizedSuggestion}
          
          <div className="bg-gray-800/50 p-2 mt-2 rounded text-xs text-gray-300">
            {currentStrategy.name}
          </div>
        </div>
        
        <div className="flex border-b border-gray-800">
          <div className="w-1/2 p-3 border-r border-gray-800">
            <div className="text-gray-500 text-xs mb-1 flex items-center">
              <TrendingUp size={12} className="mr-1" /> Taxa de Acerto
            </div>
            {memoizedWinRate}
          </div>
          <div className="w-1/2 p-3">
            <div className="text-gray-500 text-xs mb-1 flex items-center">
              <ChartBar size={12} className="mr-1" /> Tendência
            </div>
            {memoizedTrendChart}
          </div>
        </div>
        
        <RouletteActionButtons 
          onDetailsClick={handleDetailsClick}
          onPlayClick={handlePlayClick}
        />
      </div>
      
      <RouletteStatsModal 
        open={statsOpen} 
        setOpen={setStatsOpen} 
        roletaName={name} 
        lastNumbers={lastNumbers}
        wins={wins}
        losses={losses}
      />
    </div>
  );
};

// Funções auxiliares
const getColorName = (num: number): string => {
  if (num === 0) return 'verde';
  const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
  return redNumbers.includes(num) ? 'vermelho' : 'preto';
};

const getColorStreak = (numbers: number[]): number => {
  if (numbers.length === 0) return 0;
  
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
  if (numbers.length < 5) return "Dados insuficientes para análise.";
  
  const colorStreak = getColorStreak(numbers);
  const winRate = wins / (wins + losses || 1) * 100;
  
  if (colorStreak >= 3) {
    return `Repetição de ${getColorName(numbers[0])} (${colorStreak}x).`;
  } else if (winRate > 55) {
    return "Taxa de acerto acima da média!";
  } else {
    return "Padrão normal detectado.";
  }
};

export default RouletteCard;
