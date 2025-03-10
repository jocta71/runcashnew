import React, { memo, useEffect, useRef } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { getRouletteNumberColor } from '@/utils/rouletteUtils';

interface LastNumbersProps {
  numbers: number[];
  isLoading: boolean;
}

const LastNumbers = memo(({ numbers, isLoading }: LastNumbersProps) => {
  // Validar números para garantir que são válidos
  const validNumbers = numbers.filter(num => num >= 0 && num <= 36);
  
  // Limitar para mostrar apenas os 10 primeiros números para economizar espaço
  const displayNumbers = validNumbers.slice(0, 10);
  
  // Referência para o número anterior
  const previousNumbersRef = useRef<number[]>([]);
  
  // Verificar qual número é novo
  const newNumberIndex = displayNumbers.length > 0 && previousNumbersRef.current.length > 0 
    ? (displayNumbers[0] !== previousNumbersRef.current[0] ? 0 : -1) 
    : -1;
  
  // Atualizar a referência após renderização
  useEffect(() => {
    // Apenas atualizar a referência se os números forem diferentes
    if (JSON.stringify(validNumbers) !== JSON.stringify(previousNumbersRef.current)) {
      previousNumbersRef.current = [...validNumbers];
    }
  }, [validNumbers]);
  
  // Log para depuração
  useEffect(() => {
    console.log('[LastNumbers] Renderizando com números:', validNumbers);
    console.log('[LastNumbers] Estado de carregamento:', isLoading);
    if (newNumberIndex === 0) {
      console.log('[LastNumbers] Novo número detectado:', validNumbers[0]);
    }
  }, [validNumbers, isLoading, newNumberIndex]);
  
  // Renderizar estado de carregamento
  if (isLoading) {
    console.log('[LastNumbers] Renderizando estado de carregamento');
    return (
      <div className="flex flex-wrap gap-1.5 my-2">
        {Array(20).fill(0).map((_, i) => (
          <Skeleton key={i} className="w-7 h-7 rounded-full" />
        ))}
      </div>
    );
  }
  
  // Renderizar mensagem se não houver números válidos
  if (validNumbers.length === 0) {
    console.log('[LastNumbers] Sem números válidos para exibir');
    return <div className="text-sm text-gray-400 my-2">Nenhum número disponível</div>;
  }
  
  // Renderizar números
  console.log('[LastNumbers] Renderizando números:', validNumbers.slice(0, 5));
  return (
    <div className="flex flex-wrap gap-0.5 my-0.5" data-testid="last-numbers">
      {displayNumbers.map((num, idx) => (
        <div
          key={`${num}-${idx}`}
          className={`w-5 h-5 rounded-full flex items-center justify-center text-[8px] font-bold 
            ${getRouletteNumberColor(num)}
            ${idx === newNumberIndex ? 'animate-pulse shadow-sm transition-all duration-500 scale-110' : ''}
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
