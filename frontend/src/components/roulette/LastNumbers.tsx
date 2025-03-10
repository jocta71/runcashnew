import React, { memo, useEffect, useState } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { getRouletteNumberColor } from '@/utils/rouletteUtils';

// Componente simplificado para evitar erros de renderização
// Removendo temporariamente os tooltips e componentes que podem causar problemas
interface LastNumbersProps {
  numbers: number[];
  isLoading: boolean;
  timestamps?: string[];
}

const LastNumbers = memo(({ numbers, isLoading, timestamps }: LastNumbersProps) => {
  // Validar números para garantir que são válidos
  const validNumbers = numbers.filter(num => num >= 0 && num <= 36);
  
  // Estado para armazenar estatísticas de sequência (opcional)
  const [streakInfo, setStreakInfo] = useState<{
    colorStreak: { color: string, count: number } | null,
    evenOddStreak: { type: string, count: number } | null,
  }>({
    colorStreak: null,
    evenOddStreak: null,
  });
  
  // Versão simplificada da detecção de sequências
  useEffect(() => {
    try {
      if (validNumbers.length >= 3) {
        // Simplificado para apenas cores e par/ímpar
        const getNumberColor = (num: number) => {
          if (num === 0) return 'green';
          return [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num) ? 'red' : 'black';
        };
        
        // Analisar só os 5 primeiros números para performance
        const firstFiveNumbers = validNumbers.slice(0, 5);
        
        // Contar sequência de cores
        let currentColor = getNumberColor(firstFiveNumbers[0]);
        let colorCount = 1;
        
        // Contar sequência de par/ímpar
        let currentEvenOdd = firstFiveNumbers[0] === 0 ? 'zero' : firstFiveNumbers[0] % 2 === 0 ? 'even' : 'odd';
        let evenOddCount = 1;
        
        for (let i = 1; i < firstFiveNumbers.length; i++) {
          const num = firstFiveNumbers[i];
          const color = getNumberColor(num);
          const evenOdd = num === 0 ? 'zero' : num % 2 === 0 ? 'even' : 'odd';
          
          if (color === currentColor) {
            colorCount++;
          } else {
            break;
          }
          
          if (evenOdd === currentEvenOdd) {
            evenOddCount++;
          } else {
            currentEvenOdd = evenOdd;
            evenOddCount = 1;
          }
        }
        
        // Atualizar estado apenas se houver sequências significativas
        setStreakInfo({
          colorStreak: colorCount >= 3 ? { color: currentColor, count: colorCount } : null,
          evenOddStreak: evenOddCount >= 3 ? { type: currentEvenOdd, count: evenOddCount } : null,
        });
      }
    } catch (error) {
      console.error("Erro na detecção de sequências:", error);
      // Em caso de erro, não mostramos nenhuma sequência
      setStreakInfo({
        colorStreak: null,
        evenOddStreak: null,
      });
    }
  }, [validNumbers]);
  
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
  
  // Renderizar informações de sequência (simplificado)
  const renderStreakInfo = () => {
    if (!streakInfo.colorStreak && !streakInfo.evenOddStreak) {
      return null;
    }
    
    return (
      <div className="text-xs mt-1 mb-2 text-gray-400 flex flex-wrap gap-2">
        {streakInfo.colorStreak && (
          <span className="bg-gray-100 dark:bg-gray-800 rounded-full px-2 py-0.5">
            {streakInfo.colorStreak.count}x {
              streakInfo.colorStreak.color === 'red' ? '🔴' : 
              streakInfo.colorStreak.color === 'black' ? '⚫' : '🟢'
            }
          </span>
        )}
        {streakInfo.evenOddStreak && (
          <span className="bg-gray-100 dark:bg-gray-800 rounded-full px-2 py-0.5">
            {streakInfo.evenOddStreak.count}x {
              streakInfo.evenOddStreak.type === 'even' ? 'Pares' : 
              streakInfo.evenOddStreak.type === 'odd' ? 'Ímpares' : 'Zero'
            }
          </span>
        )}
      </div>
    );
  };
  
  // Renderizar números (sem tooltips por enquanto)
  console.log('[LastNumbers] Renderizando números:', validNumbers.slice(0, 5));
  return (
    <>
      {renderStreakInfo()}
      <div className="flex flex-wrap gap-1.5 my-2" data-testid="last-numbers">
        {validNumbers.map((num, idx) => (
          <div
            key={`${num}-${idx}`}
            className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${getRouletteNumberColor(num)} relative`}
            data-number={num}
          >
            {num}
            {idx === 0 && (
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full" />
            )}
          </div>
        ))}
      </div>
    </>
  );
});

LastNumbers.displayName = 'LastNumbers';

export default LastNumbers;
