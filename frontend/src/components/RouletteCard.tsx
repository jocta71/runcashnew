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
  const [lastNumbers, setLastNumbers] = useState<number[]>(initialLastNumbers);
  const [previousLastNumber, setPreviousLastNumber] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [dataSeeded, setDataSeeded] = useState(false);
  const [statsOpen, setStatsOpen] = useState(false);

  useEffect(() => {
    const checkAndSeedData = async () => {
      try {
        console.log("Verificando dados no Supabase...");
        
        const response = await fetch(
          'https://evzqzghxuttctbxgohpx.supabase.co/rest/v1/roletas?select=count',
          {
            headers: {
              'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ',
              'Content-Type': 'application/json'
            }
          }
        );
        
        if (!response.ok) {
          console.error('Erro ao verificar a tabela roletas');
          setLastNumbers(initialLastNumbers);
          setDataSeeded(true);
          return;
        }
        
        const data = await response.json();
        console.log('Resposta da verificação da tabela:', data);
        
        if (!data || data.length === 0) {
          console.log('Nenhum dado encontrado, usando dados locais');
          setLastNumbers(initialLastNumbers);
          setDataSeeded(true);
          toast({
            title: 'Usando Dados Locais',
            description: 'Conecte um raspador para dados em tempo real',
            variant: 'default',
          });
        } else {
          console.log('Dados existentes no banco, tentando carregar');
          setDataSeeded(true);
        }
      } catch (error) {
        console.error('Erro ao verificar dados:', error);
        setLastNumbers(initialLastNumbers);
        setDataSeeded(true);
      }
    };

    checkAndSeedData();
  }, [initialLastNumbers]);

  const fetchRouletteNumbers = useCallback(async () => {
    try {
      setIsLoading(true);
      console.log(`Buscando números para roleta: ${name}`);
      
      const response = await fetch(
        `https://evzqzghxuttctbxgohpx.supabase.co/rest/v1/roletas?nome=eq.${encodeURIComponent(name)}&select=numeros`,
        {
          headers: {
            'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ',
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (!response.ok) {
        throw new Error(`Erro ao buscar dados: ${response.statusText}`);
      }
      
      const data = await response.json();
      console.log(`Dados recebidos para ${name}:`, data);
      
      if (data && data.length > 0 && Array.isArray(data[0].numeros)) {
        const numerosFiltrados = data[0].numeros
          .map((num: any) => typeof num === 'string' ? parseInt(num, 10) : Number(num))
          .filter((num: number) => !isNaN(num) && num >= 0 && num <= 36);
        
        if (numerosFiltrados.length > 0) {
          console.log(`Atualizando números para ${name}:`, numerosFiltrados);
          setLastNumbers(numerosFiltrados);
        } else {
          console.log(`Sem números válidos para ${name}, mantendo padrão`);
        }
      }
    } catch (error) {
      console.error(`Erro ao buscar números para ${name}:`, error);
    } finally {
      setIsLoading(false);
    }
  }, [name]);

  useEffect(() => {
    if (dataSeeded) {
      // Busca inicial
      fetchRouletteNumbers();
      
      // Configurar polling para atualizar a cada 10 segundos
      const intervalId = setInterval(fetchRouletteNumbers, 10000);
      
      // Limpar intervalo quando o componente for desmontado
      return () => clearInterval(intervalId);
    }
  }, [dataSeeded, fetchRouletteNumbers]);

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
    navigate(`/roulette/${encodeURIComponent(name)}`);
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
        <TrendingUp size={20} className="text-[#00ff00]" />
      </div>
      
      {memoizedNumbers}
      {memoizedSuggestion}
      {memoizedWinRate}
      {memoizedTrendChart}
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
                key={idx}
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

export default RouletteCard;
