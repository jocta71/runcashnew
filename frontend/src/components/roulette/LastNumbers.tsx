import React, { memo, useEffect, useState } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import { getRouletteNumberColor } from '@/utils/rouletteUtils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface LastNumbersProps {
  numbers: number[];
  isLoading: boolean;
  timestamps?: string[]; // Opcional: timestamps dos números, se disponíveis
}

const LastNumbers = memo(({ numbers, isLoading, timestamps }: LastNumbersProps) => {
  // Validar números para garantir que são válidos
  const validNumbers = numbers.filter(num => num >= 0 && num <= 36);
  
  // Estado para armazenar estatísticas de sequência
  const [streakInfo, setStreakInfo] = useState<{
    colorStreak: { color: string, count: number } | null,
    evenOddStreak: { type: string, count: number } | null,
    dozenStreak: { dozen: string, count: number } | null,
    halfStreak: { half: string, count: number } | null,
  }>({
    colorStreak: null,
    evenOddStreak: null,
    dozenStreak: null,
    halfStreak: null,
  });
  
  // Calcular informações de sequência quando os números mudam
  useEffect(() => {
    if (validNumbers.length >= 3) {
      // Funções auxiliares
      const getNumberColor = (num: number) => {
        if (num === 0) return 'green';
        return [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num) ? 'red' : 'black';
      };
      
      const getDozen = (num: number) => {
        if (num === 0) return 'zero';
        if (num <= 12) return 'first';
        if (num <= 24) return 'second';
        return 'third';
      };
      
      // Analisar últimos números para sequências
      let currentColorStreak = { color: getNumberColor(validNumbers[0]), count: 1 };
      let currentEvenOddStreak = { 
        type: validNumbers[0] === 0 ? 'zero' : validNumbers[0] % 2 === 0 ? 'even' : 'odd', 
        count: 1 
      };
      let currentDozenStreak = { dozen: getDozen(validNumbers[0]), count: 1 };
      let currentHalfStreak = { 
        half: validNumbers[0] === 0 ? 'zero' : validNumbers[0] <= 18 ? 'low' : 'high', 
        count: 1 
      };
      
      // Contar sequências
      for (let i = 1; i < validNumbers.length; i++) {
        const currentNum = validNumbers[i];
        const currentColor = getNumberColor(currentNum);
        const currentEvenOdd = currentNum === 0 ? 'zero' : currentNum % 2 === 0 ? 'even' : 'odd';
        const currentDozen = getDozen(currentNum);
        const currentHalf = currentNum === 0 ? 'zero' : currentNum <= 18 ? 'low' : 'high';
        
        // Verificar cor
        if (currentColor === currentColorStreak.color) {
          currentColorStreak.count++;
        } else {
          break;
        }
        
        // Verificar par/ímpar
        if (currentEvenOdd === currentEvenOddStreak.type) {
          currentEvenOddStreak.count++;
        } else {
          currentEvenOddStreak = { type: currentEvenOdd, count: 1 };
        }
        
        // Verificar dúzia
        if (currentDozen === currentDozenStreak.dozen) {
          currentDozenStreak.count++;
        } else {
          currentDozenStreak = { dozen: currentDozen, count: 1 };
        }
        
        // Verificar metade
        if (currentHalf === currentHalfStreak.half) {
          currentHalfStreak.count++;
        } else {
          currentHalfStreak = { half: currentHalf, count: 1 };
        }
      }
      
      // Atualizar estado com informações de sequência
      setStreakInfo({
        colorStreak: currentColorStreak.count >= 3 ? currentColorStreak : null,
        evenOddStreak: currentEvenOddStreak.count >= 3 ? currentEvenOddStreak : null,
        dozenStreak: currentDozenStreak.count >= 3 ? currentDozenStreak : null,
        halfStreak: currentHalfStreak.count >= 3 ? currentHalfStreak : null,
      });
    }
  }, [validNumbers]);
  
  // Log para depuração
  useEffect(() => {
    console.log('[LastNumbers] Renderizando com números:', validNumbers);
    console.log('[LastNumbers] Estado de carregamento:', isLoading);
    if (timestamps) console.log('[LastNumbers] Timestamps disponíveis:', timestamps);
  }, [validNumbers, isLoading, timestamps]);
  
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

  // Renderizar informações de sequência
  const renderStreakInfo = () => {
    if (!streakInfo.colorStreak && !streakInfo.evenOddStreak && 
        !streakInfo.dozenStreak && !streakInfo.halfStreak) {
      return null;
    }
    
    return (
      <div className="text-xs mt-1 mb-2 text-gray-400 flex flex-wrap gap-2">
        {streakInfo.colorStreak && (
          <span className="bg-gray-100 dark:bg-gray-800 rounded-full px-2 py-0.5">
            {streakInfo.colorStreak.count}x {streakInfo.colorStreak.color === 'red' ? '🔴' : 
              streakInfo.colorStreak.color === 'black' ? '⚫' : '🟢'}
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
        {streakInfo.dozenStreak && (
          <span className="bg-gray-100 dark:bg-gray-800 rounded-full px-2 py-0.5">
            {streakInfo.dozenStreak.count}x {
              streakInfo.dozenStreak.dozen === 'first' ? '1ª dúzia' : 
              streakInfo.dozenStreak.dozen === 'second' ? '2ª dúzia' : 
              streakInfo.dozenStreak.dozen === 'third' ? '3ª dúzia' : 'Zero'
            }
          </span>
        )}
        {streakInfo.halfStreak && (
          <span className="bg-gray-100 dark:bg-gray-800 rounded-full px-2 py-0.5">
            {streakInfo.halfStreak.count}x {
              streakInfo.halfStreak.half === 'low' ? '1-18' : 
              streakInfo.halfStreak.half === 'high' ? '19-36' : 'Zero'
            }
          </span>
        )}
      </div>
    );
  };
  
  // Renderizar números com tooltips
  console.log('[LastNumbers] Renderizando números:', validNumbers.slice(0, 5));
  return (
    <>
      {renderStreakInfo()}
      <div className="flex flex-wrap gap-1.5 my-2" data-testid="last-numbers">
        {validNumbers.map((num, idx) => (
          <TooltipProvider key={`${num}-${idx}`}>
            <Tooltip>
              <TooltipTrigger asChild>
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${getRouletteNumberColor(num)} relative`}
                  data-number={num}
                >
                  {num}
                  {idx === 0 && (
                    <span className="absolute -top-1 -right-1 w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                  )}
                </div>
              </TooltipTrigger>
              <TooltipContent className="text-xs">
                <p><strong>Número:</strong> {num}</p>
                <p><strong>Posição:</strong> {idx + 1}º</p>
                {timestamps && timestamps[idx] && (
                  <p><strong>Horário:</strong> {
                    format(new Date(timestamps[idx]), 'HH:mm:ss', {locale: ptBR})
                  }</p>
                )}
                <p><strong>Cor:</strong> {
                  num === 0 ? 'Verde' : 
                  [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num) ? 'Vermelho' : 'Preto'
                }</p>
                <p><strong>Tipo:</strong> {num === 0 ? 'Zero' : num % 2 === 0 ? 'Par' : 'Ímpar'}</p>
                <p><strong>Dúzia:</strong> {
                  num === 0 ? 'Zero' : 
                  num <= 12 ? 'Primeira' : 
                  num <= 24 ? 'Segunda' : 'Terceira'
                }</p>
                <p><strong>Metade:</strong> {
                  num === 0 ? 'Zero' : 
                  num <= 18 ? 'Baixa (1-18)' : 'Alta (19-36)'
                }</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        ))}
      </div>
    </>
  );
});

LastNumbers.displayName = 'LastNumbers';

export default LastNumbers;
