import React, { useEffect, useState } from 'react';
import { WandSparkles, Eye, EyeOff } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import Lottie from 'lottie-react';
import RouletteNumber from './RouletteNumber';

interface SuggestionDisplayProps {
  suggestion: string;
  isBlurred: boolean;
  showSuggestions: boolean;
}

const SuggestionDisplay = ({ 
  suggestion, 
  isBlurred,
  showSuggestions
}: SuggestionDisplayProps) => {
  const [animationData, setAnimationData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  
  // Carregar a animação de loading quando o componente for montado
  useEffect(() => {
    const fetchAnimationData = async () => {
      try {
        const response = await fetch('https://lottie.host/e7682e8a-7fbe-4fd3-bc3f-6d65c40af72b/ZnEC1IVpOl.json');
        const data = await response.json();
        setAnimationData(data);
        setIsLoading(false);
      } catch (error) {
        console.error("Erro ao carregar a animação de loading:", error);
        setIsLoading(false);
      }
    };

    fetchAnimationData();
  }, []);
  
  // Função simples para determinar a cor com base no número
  const getSuggestionColor = (num: number) => {
    if (num === 0) return 'bg-green-600';
    return num % 2 === 0 ? 'bg-red-600' : 'bg-black';
  };

  if (!showSuggestions) {
    return null;
  }

  // Converter a string de sugestão em array de números
  const suggestionNumbers = suggestion
    .split(',')
    .map(num => parseInt(num.trim()))
    .filter(num => !isNaN(num));

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <WandSparkles size={18} className="text-vegas-gold" />
          <span className="text-sm text-vegas-gold font-medium">Sugestão de Jogada</span>
        </div>
      </div>
      
      <div className={`flex justify-start gap-2 ${isBlurred ? 'blur-md' : ''}`}>
        {suggestionNumbers.length > 0 ? (
          // Mostrar os números da sugestão quando disponíveis
          suggestionNumbers.map((num, index) => (
            <RouletteNumber 
              key={index} 
              number={num} 
              size="md" 
              className={getSuggestionColor(num)}
            />
          ))
        ) : (
          // Mostrar a animação de loading quando não há sugestões
          animationData && (
            <div className="h-12 w-full flex justify-start items-center">
              <Lottie
                animationData={animationData}
                loop={true}
                autoplay={true}
                style={{ height: '100%', width: 'auto' }}
              />
            </div>
          )
        )}
      </div>
    </div>
  );
};

export default React.memo(SuggestionDisplay);
