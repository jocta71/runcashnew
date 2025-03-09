import React, { useEffect } from 'react';
import RouletteNumber from './RouletteNumber';
import { Loader2 } from 'lucide-react';

interface LastNumbersProps {
  numbers: number[];
  isLoading?: boolean;
}

const LastNumbers = ({ numbers, isLoading = false }: LastNumbersProps) => {
  // Garantir que todos são números válidos
  const validNumbers = Array.isArray(numbers) 
    ? numbers
        .filter(num => num !== undefined && num !== null)
        .map(num => typeof num === 'string' ? parseInt(num as string, 10) : Number(num))
        .filter(num => !isNaN(num) && num >= 0 && num <= 36)
    : [];

  useEffect(() => {
    console.log('LastNumbers recebeu:', numbers);
    console.log('LastNumbers validados:', validNumbers);
  }, [numbers, validNumbers]);

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
