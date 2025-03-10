import { memo } from 'react';

interface LastNumbersProps {
  numbers: number[];
  isLoading: boolean;
}

// Função simplificada para obter cor do número
const getNumberColor = (num: number): string => {
  if (num === 0) {
    return "bg-green-600 text-white";
  } else if ([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num)) {
    return "bg-red-600 text-white";
  } else {
    return "bg-gray-900 text-white";
  }
};

// Componente extremamente simplificado, sem estado, sem efeitos
const LastNumbers = memo(({ numbers, isLoading }: LastNumbersProps) => {
  // Filtragem básica de números
  const validNumbers = numbers.filter(n => n >= 0 && n <= 36);
  
  // Estado de carregamento
  if (isLoading) {
    return (
      <div className="flex flex-wrap gap-1.5 my-2">
        <div className="text-sm">Carregando números...</div>
      </div>
    );
  }
  
  // Sem números
  if (validNumbers.length === 0) {
    return <div className="text-sm text-gray-400 my-2">Nenhum número disponível</div>;
  }
  
  // Apenas renderizar números
  return (
    <div className="flex flex-wrap gap-1.5 my-2" data-testid="last-numbers">
      {validNumbers.map((num, idx) => (
        <div
          key={`${num}-${idx}`}
          className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${getNumberColor(num)}`}
        >
          {num}
        </div>
      ))}
    </div>
  );
});

LastNumbers.displayName = 'LastNumbers';

export default LastNumbers;
