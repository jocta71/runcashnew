import React, { memo, useEffect, useRef } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { getRouletteNumberColor } from '@/utils/rouletteUtils';

interface LastNumbersProps {
  numbers: number[];
  isLoading: boolean;
}

// Objeto global para armazenar o último estado renderizado de cada componente
const lastRenderedStates: Record<string, number[]> = {};

const LastNumbers = memo(({ numbers, isLoading }: LastNumbersProps) => {
  // Usando uma ref para manter o estado visual consistente durante remontagens
  const stableNumbersRef = useRef<number[]>([]);
  
  // ID único para este componente (baseado na string dos números)
  const componentId = useRef<string>(`last-numbers-${Date.now()}`);
  
  // Verificar se temos números anteriores armazenados
  useEffect(() => {
    const id = componentId.current;
    
    // Ao montar, verificar se já temos um estado anterior
    if (lastRenderedStates[id] && lastRenderedStates[id].length > 0) {
      // Usar os números do último estado renderizado para evitar piscar
      stableNumbersRef.current = lastRenderedStates[id];
    } else if (numbers.length > 0) {
      // Se não temos estado anterior, mas temos números, usar os números atuais
      stableNumbersRef.current = numbers;
      // E também armazenar no estado global
      lastRenderedStates[id] = [...numbers];
    }
    
    // Limpeza
    return () => {
      // Manter o estado ao desmontar para possível reutilização
      lastRenderedStates[id] = stableNumbersRef.current;
    };
  }, []);
  
  // Atualizar o estado ref apenas quando números mudam e não estão vazios
  useEffect(() => {
    if (numbers.length > 0) {
      const id = componentId.current;
      stableNumbersRef.current = numbers;
      lastRenderedStates[id] = [...numbers];
    }
  }, [numbers]);
  
  // Validar números para garantir que são válidos
  const getValidNumbers = () => {
    // Usar números da ref para estabilidade visual
    const currentNumbers = stableNumbersRef.current.length > 0 
      ? stableNumbersRef.current 
      : numbers;
      
    return currentNumbers.filter(num => num >= 0 && num <= 36);
  };
  
  // Verificar qual número é novo
  const validNumbers = getValidNumbers();
  const previousNumbersRef = useRef<number[]>([]);
  
  const newNumberIndex = validNumbers.length > 0 && previousNumbersRef.current.length > 0 
    ? (validNumbers[0] !== previousNumbersRef.current[0] ? 0 : -1) 
    : -1;
  
  // Atualizar a referência após renderização
  useEffect(() => {
    // Apenas atualizar a referência se os números forem diferentes
    if (validNumbers.length > 0 && 
        JSON.stringify(validNumbers) !== JSON.stringify(previousNumbersRef.current)) {
      previousNumbersRef.current = [...validNumbers];
    }
  }, [validNumbers]);
  
  // Log mínimo para evitar poluição do console
  useEffect(() => {
    if (validNumbers.length > 0 && newNumberIndex === 0) {
      console.log('[LastNumbers] Novo número detectado:', validNumbers[0]);
    }
  }, [validNumbers, newNumberIndex]);
  
  // Se estiver carregando e não temos números, mostrar esqueletos
  if (isLoading && validNumbers.length === 0) {
    return (
      <div className="flex flex-wrap gap-1.5 my-2 no-transition">
        {Array(10).fill(0).map((_, i) => (
          <Skeleton key={i} className="w-7 h-7 rounded-full" />
        ))}
      </div>
    );
  }
  
  // Se não temos números válidos, mostrar mensagem
  if (validNumbers.length === 0) {
    return <div className="text-sm text-gray-400 my-2 no-transition">Nenhum número disponível</div>;
  }
  
  // Renderizar números com transição suave apenas para o novo número
  return (
    <div className="flex flex-wrap gap-1.5 my-2 no-transition" data-testid="last-numbers">
      {validNumbers.map((num, idx) => (
        <div
          key={`${num}-${idx}`}
          className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold 
            ${getRouletteNumberColor(num)}
            ${idx === newNumberIndex ? 'animate-pulse shadow-lg transition-all duration-500 scale-110' : ''}
          `}
          data-number={num}
          data-new={idx === newNumberIndex ? 'true' : 'false'}
        >
          {num}
        </div>
      ))}
    </div>
  );
});

LastNumbers.displayName = 'LastNumbers';

export default LastNumbers;
