import React, { useState, useEffect, memo } from 'react';

interface LatestNumberProps {
  number: number | null;
  isLoading?: boolean;
}

const LatestNumber = memo(({ number }: LatestNumberProps) => {
  const [animate, setAnimate] = useState(false);
  const [prevNumber, setPrevNumber] = useState<number | null>(null);
  
  // Efeito para animar quando o número mudar
  useEffect(() => {
    if (number !== null && number !== prevNumber) {
      setAnimate(true);
      setPrevNumber(number);
      
      const timeout = setTimeout(() => {
        setAnimate(false);
      }, 2000);
      
      return () => clearTimeout(timeout);
    }
  }, [number, prevNumber]);
  
  if (number === null) {
    return (
      <div className="flex justify-center my-4">
        <div className="bg-gray-700 text-gray-400 rounded-full w-16 h-16 flex items-center justify-center text-2xl">
          ?
        </div>
      </div>
    );
  }
  
  return (
    <div className="flex justify-center my-4">
      <div 
        className={`bg-vegas-gold text-black font-bold rounded-full w-16 h-16 flex items-center justify-center text-2xl ${
          animate ? 'animate-scale-in' : ''
        }`}
      >
        {number}
      </div>
    </div>
  );
});

// Adicionar um displayName para facilitar a depuração
LatestNumber.displayName = 'LatestNumber';

export default LatestNumber;
