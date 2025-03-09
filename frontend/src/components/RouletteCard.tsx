import { TrendingUp } from 'lucide-react';
import { useState, useEffect } from 'react';
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

  useEffect(() => {
    const fetchRouletteNumbers = async () => {
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
            validNumbers = data[0].numeros
              .map(num => typeof num === 'string' ? parseInt(num, 10) : num)
              .filter(num => !isNaN(num))
              .slice(0, 20);
          }
          
          console.log(`Números processados para ${name}:`, validNumbers);
          
          if (validNumbers.length > 0) {
            setLastNumbers(validNumbers);
          } else {
            console.log(`Nenhum número válido encontrado para ${name}, usando dados iniciais`);
            setLastNumbers(initialLastNumbers);
          }
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
    };

    if (dataSeeded) {
      fetchRouletteNumbers();
      
      const intervalId = setInterval(fetchRouletteNumbers, 10000);
      
      return () => clearInterval(intervalId);
    }
  }, [name, dataSeeded, initialLastNumbers]);

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

  return (
    <div 
      className="bg-[#17161e]/90 backdrop-filter backdrop-blur-sm border border-white/10 rounded-xl p-4 space-y-3 animate-fade-in hover-scale cursor-pointer h-auto"
      onClick={handleDetailsClick}
    >
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">{name}</h3>
        <TrendingUp size={20} className="text-[#00ff00]" />
      </div>
      
      <LastNumbers numbers={lastNumbers} isLoading={isLoading} />
      
      <SuggestionDisplay 
        suggestion={suggestion}
        selectedGroup={selectedGroup}
        isBlurred={isBlurred}
        toggleVisibility={toggleVisibility}
        numberGroups={numberGroups}
      />
      
      <WinRateDisplay wins={wins} losses={losses} />
      
      <RouletteTrendChart trend={trend} />
      
      <RouletteActionButtons 
        onDetailsClick={handleDetailsClick}
        onPlayClick={handlePlayClick}
      />
    </div>
  );
};

export default RouletteCard;
