import { TrendingUp, ChartBar, ArrowUp, Eye, EyeOff, History, Target, Percent, Star, AlertTriangle, RefreshCw } from 'lucide-react';
import { useState, useMemo } from 'react';
import { toast } from '@/components/ui/use-toast';
import { useNavigate } from 'react-router-dom';
import { strategies, numberGroups } from './roulette/constants';
import LastNumbers from './roulette/LastNumbers';
import WinRateDisplay from './roulette/WinRateDisplay';
import RouletteTrendChart from './roulette/RouletteTrendChart';
import SuggestionDisplay from './roulette/SuggestionDisplay';
import RouletteActionButtons from './roulette/RouletteActionButtons';
import RouletteStatsModal from './roulette/RouletteStatsModal';
import { useRouletteData } from '@/hooks/useRouletteData';
import { Button } from '@/components/ui/button';

// Função para gerar insights com base nos números
const getInsightMessage = (numbers: number[], wins: number, losses: number) => {
  if (!numbers || numbers.length === 0) {
    return "Aguardando dados...";
  }
  
  // Verificar repetições de dúzias
  const lastFiveNumbers = numbers.slice(0, 5);
  const firstDozen = lastFiveNumbers.filter(n => n >= 1 && n <= 12).length;
  const secondDozen = lastFiveNumbers.filter(n => n >= 13 && n <= 24).length;
  const thirdDozen = lastFiveNumbers.filter(n => n >= 25 && n <= 36).length;
  
  if (firstDozen >= 3) {
    return "Primeira dúzia aparecendo com frequência";
  } else if (secondDozen >= 3) {
    return "Segunda dúzia aparecendo com frequência";
  } else if (thirdDozen >= 3) {
    return "Terceira dúzia aparecendo com frequência";
  }
  
  // Verificar números pares ou ímpares
  const oddCount = lastFiveNumbers.filter(n => n % 2 === 1).length;
  const evenCount = lastFiveNumbers.filter(n => n % 2 === 0 && n !== 0).length;
  
  if (oddCount >= 4) {
    return "Tendência para números ímpares";
  } else if (evenCount >= 4) {
    return "Tendência para números pares";
  }
  
  // Verificar números baixos ou altos
  const lowCount = lastFiveNumbers.filter(n => n >= 1 && n <= 18).length;
  const highCount = lastFiveNumbers.filter(n => n >= 19 && n <= 36).length;
  
  if (lowCount >= 4) {
    return "Tendência para números baixos (1-18)";
  } else if (highCount >= 4) {
    return "Tendência para números altos (19-36)";
  }
  
  // Baseado na taxa de vitória
  const winRate = wins / (wins + losses);
  if (winRate > 0.7) {
    return "Boa taxa de acerto! Continue com a estratégia";
  } else if (winRate < 0.3) {
    return "Taxa de acerto baixa, considere mudar a estratégia";
  }
  
  return "Padrão normal, observe mais alguns números";
};

// Gera dados de tendência baseados na taxa de vitória e derrota
const generateTrendFromWinRate = (wins: number, losses: number) => {
  const total = wins + losses;
  if (total === 0) {
    // Se não houver dados, gerar tendência aleatória
    return Array.from({ length: 20 }, () => ({ value: Math.random() * 100 }));
  }
  
  // Calcula taxa de vitória
  const winRate = wins / total;
  
  // Gera pontos de dados de tendência baseados na taxa de vitória
  return Array.from({ length: 20 }, (_, i) => {
    // Variação aleatória para simular flutuação, mas tendendo para a taxa de vitória real
    const randomVariation = (Math.random() - 0.5) * 30;
    return { value: winRate * 100 + randomVariation };
  });
};

interface RouletteCardRealtimeProps {
  roletaId: string;
  name?: string;
  roleta_nome?: string;
  wins?: number;
  losses?: number;
}

const RouletteCardRealtime = ({ 
  roletaId,
  name, 
  roleta_nome, 
  wins = 0, 
  losses = 0
}: RouletteCardRealtimeProps) => {
  const navigate = useNavigate();
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [suggestion, setSuggestion] = useState<number[]>([]);
  const [isBlurred, setIsBlurred] = useState(false);
  const [currentStrategy, setCurrentStrategy] = useState(strategies[0]);
  const [selectedGroup, setSelectedGroup] = useState<string>("grupo-123");
  const [statsOpen, setStatsOpen] = useState(false);
  
  // Verificar se o nome da roleta é válido, com fallback para roleta_nome
  const roletaNome = name || roleta_nome || "Roleta Desconhecida";
  
  // Usar o hook personalizado para obter dados em tempo real
  const { numbers, loading: isLoading, error, isConnected, hasData } = useRouletteData(roletaId, roletaNome);
  
  // Converter os objetos RouletteNumber para números simples para compatibilidade com componentes existentes
  const lastNumbers = useMemo(() => {
    return numbers.map(numObj => numObj.numero);
  }, [numbers]);
  
  const trend = useMemo(() => {
    return generateTrendFromWinRate(wins, losses);
  }, [wins, losses]);

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
  
  // Função para tentar recarregar os dados
  const reloadData = (e: React.MouseEvent) => {
    e.stopPropagation();
    window.location.reload();
  };

  // Conteúdo quando não há dados disponíveis
  const noDataContent = (
    <div className="flex flex-col items-center justify-center h-full py-8 text-center">
      <AlertTriangle size={40} className="text-yellow-500 mb-3" />
      <h3 className="text-white text-lg font-semibold mb-2">Sem Dados Disponíveis</h3>
      <p className="text-gray-400 text-sm mb-4">
        Não há números registrados no MongoDB para esta roleta.
      </p>
      <Button 
        className="flex items-center gap-2 bg-vegas-gold text-black hover:bg-vegas-gold/80"
        onClick={reloadData}
      >
        <RefreshCw size={16} />
        Recarregar
      </Button>
    </div>
  );

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
      className="bg-[#17161e]/90 backdrop-filter backdrop-blur-sm border border-white/10 rounded-xl p-3 md:p-4 space-y-2 md:space-y-3 animate-fade-in hover-scale cursor-pointer h-auto w-full overflow-hidden"
      onClick={handleDetailsClick}
    >
      {/* Header com Nome da Roleta */}
      <div className="flex items-center justify-between mb-2 border-b border-white/10 pb-2">
        <div className="flex items-center gap-2">
          <div className="text-lg font-bold text-white truncate max-w-[180px]">
            {roletaNome}
          </div>
          
          {/* Indicador de status de conexão em tempo real */}
          <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} 
              title={isConnected ? 'Conectado em tempo real' : 'Sem conexão em tempo real'} />
        </div>
        
        <div className="flex items-center gap-1">
          {/* Pequena visualização do trend */}
          <div className="text-xs text-green-400 flex items-center gap-1">
            <TrendingUp size={12} />
            <span>{wins}</span>
          </div>
          <div className="mx-1 text-gray-400">/</div>
          <div className="text-xs text-red-400 flex items-center gap-1">
            <TrendingUp size={12} className="transform rotate-180" />
            <span>{losses}</span>
          </div>
        </div>
      </div>
      
      {/* Conteúdo principal */}
      <div className="flex flex-col h-full">
        {isLoading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-vegas-gold"></div>
          </div>
        ) : !hasData ? (
          noDataContent
        ) : (
          <>
            {/* Números Recentes */}
            <div className="mb-3">
              <div className="flex items-center justify-between mb-1">
                <div className="text-xs text-gray-400 flex items-center gap-1">
                  <History size={12} />
                  <span>Números Recentes</span>
                </div>
              </div>
              {memoizedNumbers}
            </div>
            
            {/* Sugestões */}
            {showSuggestions && (
              <div className="mb-3">
                <div className="flex items-center justify-between mb-1">
                  <div className="text-xs text-gray-400 flex items-center gap-1">
                    <Target size={12} />
                    <span>Sugestões</span>
                  </div>
                  <button 
                    className="text-xs text-gray-400 hover:text-white transition-colors"
                    onClick={toggleVisibility}
                  >
                    {isBlurred ? <EyeOff size={12} /> : <Eye size={12} />}
                  </button>
                </div>
                {memoizedSuggestion}
              </div>
            )}
            
            {/* Win Rate e Trend juntos numa linha */}
            <div className="grid grid-cols-2 gap-3 mb-3">
              <div>
                <div className="text-xs text-gray-400 flex items-center gap-1 mb-1">
                  <Percent size={12} />
                  <span>Taxa de Acerto</span>
                </div>
                {memoizedWinRate}
              </div>
              
              <div>
                <div className="text-xs text-gray-400 flex items-center gap-1 mb-1">
                  <ChartBar size={12} />
                  <span>Tendência</span>
                </div>
                {memoizedTrendChart}
              </div>
            </div>
            
            {/* Insights */}
            <div className="mb-3">
              <div className="text-xs text-gray-400 flex items-center gap-1 mb-1">
                <AlertTriangle size={12} />
                <span>Insights</span>
              </div>
              <div className="text-sm bg-[#221f2e]/50 rounded-lg p-2 border border-indigo-500/20">
                <div className="flex gap-1 items-center">
                  <Star className="text-yellow-500" size={14} />
                  <span className="text-white">
                    {getInsightMessage(lastNumbers, wins, losses)}
                  </span>
                </div>
              </div>
            </div>
            
            {memoizedActionButtons}
          </>
        )}

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
    </div>
  );
};

export default RouletteCardRealtime; 