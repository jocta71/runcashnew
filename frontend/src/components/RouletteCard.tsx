import { TrendingUp } from 'lucide-react';
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

      if (data && data.length > 0 && data[0].numeros) {
        let validNumbers = [];
        
        if (Array.isArray(data[0].numeros)) {
          // Pega os números, converte para inteiros e filtra valores inválidos
          validNumbers = data[0].numeros
            .map(num => typeof num === 'string' ? parseInt(num, 10) : num)
            .filter(num => !isNaN(num));
          
          // Verificamos se temos um número novo antes de atualizar o estado
          const currentLastNumber = validNumbers.length > 0 ? validNumbers[validNumbers.length - 1] : null;
          
          // Se temos um último número e ele é diferente do anterior, atualizamos
          if (currentLastNumber !== null && currentLastNumber !== previousLastNumber) {
            console.log(`Novo número detectado para ${name}: ${currentLastNumber}`);
            setPreviousLastNumber(currentLastNumber);
            
            // Ordena os números em ordem inversa para que os mais recentes apareçam primeiro
            // Limita a 20 números para exibição
            const reversedNumbers = [...validNumbers].reverse().slice(0, 20);
            setLastNumbers(reversedNumbers);
          }
        }
        
        console.log(`Números processados para ${name}:`, validNumbers.slice(-5));
      } else {
        console.log(`Dados inválidos recebidos para ${name}, usando dados iniciais`);
        setLastNumbers(initialLastNumbers);
      }
    } catch (error) {
      console.error(`Erro buscando números para ${name}:`, error);
      setLastNumbers(initialLastNumbers);
    } finally {
      setIsLoading(false);
    }
  }, [name, initialLastNumbers, previousLastNumber]);

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
    </div>
  );
};

export default RouletteCard;
