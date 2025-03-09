import { TrendingUp, ChartBar } from 'lucide-react';
import { useState, useEffect, useCallback, useMemo } from 'react';
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
import { fetchRouletteLatestNumbers } from '@/integrations/api/rouletteService';

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
  // Novo estado para rastrear se os números vêm do Supabase
  const [usingSupabaseData, setUsingSupabaseData] = useState(false);

  useEffect(() => {
    console.log("Componente RouletteCard inicializado para roleta:", name);
    
    const checkAndSeedData = async () => {
      try {
        console.log(`[${name}] Verificando dados no Supabase...`);
        setIsLoading(true);
        
        const response = await fetch(
          'https://evzqzghxuttctbxgohpx.supabase.co/rest/v1/roletas?select=count',
          {
            headers: {
              'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ',
              'Content-Type': 'application/json',
              'Cache-Control': 'no-cache, no-store'
            }
          }
        );
        
        if (!response.ok) {
          console.error(`[${name}] Erro ao verificar a tabela roletas:`, response.statusText);
          setDataSeeded(true);
          return;
        }
        
        const data = await response.json();
        console.log(`[${name}] Resposta da verificação da tabela:`, data);
        
        if (!data || data.length === 0) {
          console.log(`[${name}] Nenhum dado encontrado, aguardando dados do Supabase...`);
          setDataSeeded(true);
        } else {
          console.log(`[${name}] Dados existentes no banco, buscando números...`);
          setDataSeeded(true);
        }
      } catch (error) {
        console.error(`[${name}] Erro ao verificar dados:`, error);
        setDataSeeded(true);
      } finally {
        setIsLoading(false);
      }
    };

    checkAndSeedData();
    // Não usar initialLastNumbers como dependência para evitar atualizações indesejadas
  }, [name]);

  const verificarEstrategia = (numero: number) => {
    // Placeholder para verificação de estratégia
    console.log(`[${name}] Verificando estratégia para número: ${numero}`);
  };

  const fetchRouletteNumbers = useCallback(async () => {
    try {
      console.log(`[${name}] [${new Date().toLocaleTimeString()}] Buscando números do Supabase...`);
      setIsLoading(true);
      
      // Primeiro tentamos buscar o ID da roleta
      const idResponse = await fetch(
        `https://evzqzghxuttctbxgohpx.supabase.co/rest/v1/roletas?nome=eq.${encodeURIComponent(name)}&select=id`,
        {
          headers: {
            'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ',
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store'
          }
        }
      );
      
      if (!idResponse.ok) {
        console.error(`[${name}] Erro ao buscar ID da roleta: ${idResponse.statusText}`);
        setIsLoading(false);
        return;
      }
      
      const idData = await idResponse.json();
      if (!idData || idData.length === 0) {
        console.error(`[${name}] Roleta não encontrada no Supabase`);
        setIsLoading(false);
        return;
      }
      
      const roletaId = idData[0].id;
      console.log(`[${name}] ID da roleta: ${roletaId}`);
      
      // Buscamos os últimos números diretamente do Supabase
      const supabaseUrl = "https://evzqzghxuttctbxgohpx.supabase.co/rest/v1/roleta_numeros";
      const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ";
      
      const response = await fetch(
        `${supabaseUrl}?roleta_id=eq.${roletaId}&select=numero,created_at&order=created_at.desc&limit=20`,
        {
          headers: {
            'apikey': supabaseKey,
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store'
          }
        }
      );
      
      if (!response.ok) {
        console.error(`[${name}] Erro ao buscar números da roleta: ${response.statusText}`);
        setIsLoading(false);
        return;
      }
      
      const data = await response.json();
      console.log(`[${name}] Dados obtidos do Supabase (${data.length} registros):`, data);
      
      if (Array.isArray(data) && data.length > 0) {
        // Extrair apenas os números na ordem correta (mais recente primeiro)
        const numbers = data.map(item => item.numero);
        console.log(`[${name}] Números extraídos do Supabase:`, numbers);
        
        // Converter para números inteiros
        const validNumbers = numbers
          .filter(num => num !== undefined && num !== null)
          .map(num => typeof num === 'string' ? parseInt(num, 10) : Number(num))
          .filter(num => !isNaN(num) && num >= 0 && num <= 36);
        
        console.log(`[${name}] Números validados do Supabase (${validNumbers.length}):`, validNumbers);
        
        if (validNumbers.length > 0) {
          // Detectar se há um novo número em comparação com o estado atual
          const isNewNumber = lastNumbers.length > 0 && validNumbers[0] !== lastNumbers[0];
          
          // Atualizar o estado com os números do Supabase
          setLastNumbers(validNumbers);
          setUsingSupabaseData(true);
          
          if (isNewNumber) {
            setPreviousLastNumber(lastNumbers[0]);
            verificarEstrategia(validNumbers[0]);
            
            // Notificar o usuário que os números foram atualizados
            toast({
              title: "Números Atualizados",
              description: `Último número: ${validNumbers[0]} (Supabase)`,
              variant: "default",
            });
          }
          
          console.log(`[${name}] Usando ${validNumbers.length} números do Supabase para exibição`);
        } else {
          console.log(`[${name}] Nenhum número válido encontrado no Supabase`);
          setUsingSupabaseData(false);
        }
      } else {
        console.log(`[${name}] Nenhum número encontrado no Supabase para a roleta`);
        setUsingSupabaseData(false);
      }
    } catch (error) {
      console.error(`[${name}] Erro ao buscar números da roleta:`, error);
      setUsingSupabaseData(false);
    } finally {
      setIsLoading(false);
    }
  }, [name, lastNumbers]);

  useEffect(() => {
    if (dataSeeded) {
      // Busca inicial imediata
      fetchRouletteNumbers();
      
      // Configurar polling para atualizar a cada 5 segundos
      const intervalId = setInterval(fetchRouletteNumbers, 5000);
      
      // Forçar uma segunda atualização após 2 segundos
      const quickRefreshTimeout = setTimeout(() => {
        console.log(`[${name}] Forçando atualização rápida para garantir exibição dos números`);
        fetchRouletteNumbers();
      }, 2000);
      
      // Limpar intervalo e timeout quando o componente for desmontado
      return () => {
        clearInterval(intervalId);
        clearTimeout(quickRefreshTimeout);
      };
    }
  }, [dataSeeded, fetchRouletteNumbers, name]);

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
    if (num === 0) {
      return 'bg-green-600 text-white'; // Verde para o zero
    } else if ([1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36].includes(num)) {
      return 'bg-red-600 text-white'; // Vermelho para números ímpares
    } else {
      return 'bg-black text-white'; // Preto para números pares
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
