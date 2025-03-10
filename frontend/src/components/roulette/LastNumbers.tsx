import React, { memo, useEffect } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { getRouletteNumberColor } from '@/utils/rouletteUtils';

interface LastNumbersProps {
  numbers: number[];
  isLoading: boolean;
}

const LastNumbers = memo(({ numbers, isLoading }: LastNumbersProps) => {
  // Validar números para garantir que são válidos
  const validNumbers = numbers.filter(num => num >= 0 && num <= 36);
  
  // Log para depuração
  useEffect(() => {
    console.log('[LastNumbers] Renderizando com números:', validNumbers);
    console.log('[LastNumbers] Estado de carregamento:', isLoading);
  }, [validNumbers, isLoading]);
  
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
    <div className="flex flex-wrap gap-1.5 my-2" data-testid="last-numbers">
      {validNumbers.map((num, idx) => (
        <div
          key={`${num}-${idx}`}
          className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${getRouletteNumberColor(num)}`}
          data-number={num}
        >
          {num}
        </div>
      ))}
    </div>
  );
});

LastNumbers.displayName = 'LastNumbers';

export default LastNumbers;
