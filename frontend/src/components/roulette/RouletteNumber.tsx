import React, { memo, useMemo } from 'react';

interface RouletteNumberProps {
  number: number;
  className?: string;
}

// Os números vermelhos na roleta
const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];

// Função para determinar a cor do número movida para fora do componente
const getRouletteNumberColor = (num: number) => {
  if (num === 0) return "bg-vegas-green text-black";
  
  if (redNumbers.includes(num)) {
    return "bg-red-600 text-white";
  } else {
    return "bg-black text-white";
  }
};

// Componente otimizado com memo para evitar re-renderizações desnecessárias
const RouletteNumber = memo(({ number, className = '' }: RouletteNumberProps) => {
  // Usando useMemo para calcular a classe de cor apenas quando o número muda
  const colorClass = useMemo(() => getRouletteNumberColor(number), [number]);

  return (
    <div
      className={`w-8 h-8 rounded-full ${colorClass} flex items-center justify-center text-sm font-medium ${className}`}
    >
      {number}
    </div>
  );
});

// Adiciona um nome de exibição para melhorar a depuração
RouletteNumber.displayName = 'RouletteNumber';

export default RouletteNumber;
