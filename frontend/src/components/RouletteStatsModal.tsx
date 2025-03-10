import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";
import { ChartBar, X } from "lucide-react";
import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { fetchRouletteLatestNumbersByName } from '@/integrations/api/rouletteService';

interface RouletteStatsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  lastNumbers: number[];
  wins: number;
  losses: number;
  trend: { value: number }[];
}

// Versão simplificada para diagnosticar o problema de renderização
const RouletteStatsModal = ({ 
  open, 
  onOpenChange, 
  name, 
  lastNumbers, 
  wins, 
  losses, 
  trend 
}: RouletteStatsModalProps) => {
  const [historicalNumbers, setHistoricalNumbers] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  useEffect(() => {
    if (open) {
      loadHistoricalData();
    }
  }, [open, name]);

  const loadHistoricalData = async () => {
    setIsLoading(true);
    try {
      // Buscar até 100 números para análise
      const result = await fetchRouletteLatestNumbersByName(name, 100);
      
      // Verificamos se temos números válidos
      if (result && result.numbers && result.numbers.length > 0) {
        setHistoricalNumbers(result.numbers);
      } else {
        // Usar os números disponíveis no componente
        setHistoricalNumbers(lastNumbers);
      }
    } catch (error) {
      console.error("Erro ao carregar dados históricos:", error);
      // Usar os números disponíveis localmente em caso de erro
      setHistoricalNumbers(lastNumbers);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Função auxiliar para obter a cor do número
  const getNumberColor = (num: number) => {
    if (num === 0) {
      return "bg-green-600 text-white";
    } else if ([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num)) {
      return "bg-red-600 text-white";
    } else {
      return "bg-gray-900 text-white";
    }
  };
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex justify-between items-center">
            <DialogTitle className="text-xl flex items-center">
              <ChartBar className="mr-2 h-5 w-5" />
              Estatísticas: {name}
            </DialogTitle>
            <DialogClose className="w-8 h-8 rounded-full flex items-center justify-center">
              <X className="h-4 w-4" />
            </DialogClose>
          </div>
          <DialogDescription>
            Análise baseada em {historicalNumbers.length} números
          </DialogDescription>
        </DialogHeader>
        
        {isLoading ? (
          <div className="py-20 text-center">
            <p>Carregando estatísticas...</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div>
              <h3 className="font-medium mb-2">Últimos Números</h3>
              <div className="flex flex-wrap gap-2">
                {historicalNumbers.slice(0, 20).map((num, idx) => (
                  <div 
                    key={idx} 
                    className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${getNumberColor(num)}`}
                  >
                    {num}
                  </div>
                ))}
              </div>
            </div>
            
            <div>
              <h3 className="font-medium mb-2">Estatísticas Básicas</h3>
              <div className="grid grid-cols-2 gap-4">
                <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded">
                  <p className="text-sm text-gray-500">Vermelho / Preto / Verde</p>
                  <p className="text-lg font-medium">
                    {historicalNumbers.filter(n => [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(n)).length} / {historicalNumbers.filter(n => [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35].includes(n)).length} / {historicalNumbers.filter(n => n === 0).length}
                  </p>
                </div>
                
                <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded">
                  <p className="text-sm text-gray-500">Par / Ímpar / Zero</p>
                  <p className="text-lg font-medium">
                    {historicalNumbers.filter(n => n !== 0 && n % 2 === 0).length} / {historicalNumbers.filter(n => n !== 0 && n % 2 !== 0).length} / {historicalNumbers.filter(n => n === 0).length}
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};

export default RouletteStatsModal;

