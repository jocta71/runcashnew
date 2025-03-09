import React from 'react';
import RouletteNumber from './RouletteNumber';
import { Loader2 } from 'lucide-react';

interface LastNumbersProps {
  numbers: number[];
  isLoading?: boolean;
}

const LastNumbers = ({ numbers, isLoading = false }: LastNumbersProps) => {
  // Garantir que todos são números válidos
  const validNumbers = Array.isArray(numbers) 
    ? numbers.filter(num => !isNaN(Number(num))).map(num => Number(num))
    : [];

  if (isLoading) {
    return (
      <div className="flex justify-center items-center h-10">
        <Loader2 size={20} className="animate-spin text-vegas-gold" />
      </div>
    );
  }

  if (validNumbers.length === 0) {
    return (
      <div className="flex justify-center items-center h-10 text-gray-400 text-sm">
        Aguardando números...
      </div>
    );
  }

  return (
    <div className="flex flex-wrap justify-center gap-2 max-w-full">
      {validNumbers.map((num, i) => (
        <RouletteNumber key={i} number={num} />
      ))}
    </div>
  );
};

export default LastNumbers;
