import { TrendingUp, ArrowUpRight, ArrowDownRight, Loader2 } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useState, useEffect, useCallback, useMemo } from 'react';
import { toast } from '@/components/ui/use-toast';
import RouletteStatsModal from '@/components/RouletteStatsModal';
import { strategies, numberGroups } from './roulette/constants';
import LastNumbers from './roulette/LastNumbers';
import WinRateDisplay from './roulette/WinRateDisplay';
import RouletteTrendChart from './roulette/RouletteTrendChart';
import SuggestionDisplay from './roulette/SuggestionDisplay';
import RouletteActionButtons from './roulette/RouletteActionButtons';
import RouletteAnimation from './roulette/RouletteAnimation';
import { fetchAllRoulettes, fetchLatestRouletteNumbers, RouletteData } from '@/integrations/api/rouletteService';

interface RouletteCardProps {
  name: string;
  lastNumbers: number[];
  latestNumber?: number | null;
  wins: number;
  losses: number;
  trend: { value: number }[];
}

const RouletteCard = ({ name, lastNumbers: initialLastNumbers, latestNumber, wins: initialWins, losses: initialLosses, trend: initialTrend }: RouletteCardProps) => {
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [suggestion, setSuggestion] = useState<string>('');
  const [isBlurred, setIsBlurred] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [lastNumbers, setLastNumbers] = useState<number[]>(initialLastNumbers || []);
  const [isLoading, setIsLoading] = useState(true);
  const [rouletteData, setRouletteData] = useState<RouletteData | null>(null);
  const [isLoadingLatest, setIsLoadingLatest] = useState(false);
  const [latestNumberValue, setLatestNumberValue] = useState<number | null>(latestNumber);
  const [wins, setWins] = useState(initialWins);
  const [losses, setLosses] = useState(initialLosses);
  const [trend, setTrend] = useState(initialTrend);
  const [currentState, setCurrentState] = useState<string>('NEUTRAL');

  // Função para buscar dados da roleta
  const fetchRouletteData = useCallback(async () => {
    try {
      const allRoulettes = await fetchAllRoulettes();
      const matchingRoulette = allRoulettes.find(roulette => roulette.nome.toLowerCase() === name.toLowerCase());
      
      if (matchingRoulette) {
        setLastNumbers(matchingRoulette.numeros.slice(0, 24));
        setRouletteData(matchingRoulette);
        setWins(matchingRoulette.vitorias || 0);
        setLosses(matchingRoulette.derrotas || 0);
        setSuggestion(matchingRoulette.sugestao_display || '');
        
        // Atualizar o estado atual para a animação
        if (matchingRoulette.estado_estrategia) {
          setCurrentState(matchingRoulette.estado_estrategia);
        }
        
        setIsLoading(false);
      }
    } catch (error) {
      console.error('Erro ao buscar dados da roleta:', error);
      setIsLoading(false);
    }
  }, [name]);

  // Função para buscar apenas o número mais recente
  const fetchLatestNumber = useCallback(async () => {
    try {
      setIsLoadingLatest(true);
      const latestData = await fetchLatestRouletteNumbers();
      const matchingRoulette = latestData.find(roulette => roulette.nome.toLowerCase() === name.toLowerCase());
      
      if (matchingRoulette) {
        if (matchingRoulette.numero_recente !== null && latestNumberValue !== matchingRoulette.numero_recente) {
          setLatestNumberValue(matchingRoulette.numero_recente);
          
          // Update lastNumbers array if the latest number is different
          if (lastNumbers.length === 0 || matchingRoulette.numero_recente !== lastNumbers[0]) {
            const newLastNumbers = [matchingRoulette.numero_recente];
            // Manter até 19 números anteriores (para um total de 20 com o novo)
            for (let i = 0; i < Math.min(19, lastNumbers.length); i++) {
              newLastNumbers.push(lastNumbers[i]);
            }
            setLastNumbers(newLastNumbers);
          }
        }
        
        // Atualizar outros dados
        setWins(matchingRoulette.vitorias || 0);
        setLosses(matchingRoulette.derrotas || 0);
        setSuggestion(matchingRoulette.sugestao_display || '');
        
        // Atualizar o estado atual para a animação
        if (matchingRoulette.estado_estrategia) {
          setCurrentState(matchingRoulette.estado_estrategia);
        }
      }
      setIsLoadingLatest(false);
    } catch (error) {
      console.error('Erro ao buscar número mais recente:', error);
      setIsLoadingLatest(false);
    }
  }, [name, latestNumberValue, lastNumbers]);

  // Polling para atualizar apenas o número mais recente a cada 2 segundos
  useEffect(() => {
    fetchLatestNumber();
    
    const intervalId = setInterval(() => {
      fetchLatestNumber();
    }, 2000);
    
    return () => clearInterval(intervalId);
  }, [fetchLatestNumber]);

  // Polling para atualizar todos os dados a cada 10 segundos
  useEffect(() => {
    fetchRouletteData();
    
    const intervalId = setInterval(() => {
      fetchRouletteData();
    }, 10000);
    
    return () => clearInterval(intervalId);
  }, [fetchRouletteData]);

  const toggleSuggestions = () => {
    setShowSuggestions(!showSuggestions);
  };

  const toggleBlur = () => {
    setIsBlurred(!isBlurred);
  };

  const openModal = () => {
    setShowModal(true);
  };

  const closeModal = () => {
    setShowModal(false);
  };

  const handlePlay = (e: React.MouseEvent) => {
    e.stopPropagation(); // Previne que o clique abra o modal
    // Redirecionar para o site do cassino ou abrir em nova janela
    window.open('https://es.888casino.com/live-casino/#filters=live-roulette', '_blank');
  };

  return (
    <>
      <div 
        className="bg-[#17161e]/90 backdrop-filter backdrop-blur-sm border border-white/10 rounded-xl p-4 space-y-3 animate-fade-in hover-scale cursor-pointer h-auto relative"
        onClick={() => openModal()}
      >
        {/* Animação com base no estado atual */}
        <RouletteAnimation state={currentState} />
        
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">{name}</h3>
          <TrendingUp size={20} className="text-vegas-green" />
        </div>
        
        {/* Container para os números com altura máxima e rolagem se necessário */}
        <div className="max-h-28 overflow-y-auto pr-1 custom-scrollbar">
          <LastNumbers numbers={lastNumbers} />
        </div>
        
        <SuggestionDisplay 
          suggestion={suggestion}
          isBlurred={isBlurred}
          showSuggestions={showSuggestions}
        />
        
        <WinRateDisplay wins={wins} losses={losses} />
        
        <RouletteTrendChart trend={trend} />
        
        <RouletteActionButtons 
          toggleSuggestions={toggleSuggestions}
          toggleBlur={toggleBlur}
          isBlurred={isBlurred}
          showSuggestions={showSuggestions}
          handlePlay={handlePlay}
        />
      </div>
      
      <RouletteStatsModal
        open={showModal}
        onOpenChange={closeModal}
        name={name}
        lastNumbers={lastNumbers}
        wins={wins}
        losses={losses}
        trend={trend}
        rouletteId={rouletteData?.id}
      />
    </>
  );
};

export default RouletteCard;
