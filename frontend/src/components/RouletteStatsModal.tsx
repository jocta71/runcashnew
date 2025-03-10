import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

interface RouletteStatsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  lastNumbers: number[];
  wins: number;
  losses: number;
  trend: { value: number }[];
}

// Modal ultra básico para diagnóstico
const RouletteStatsModal = ({ 
  open, 
  onOpenChange, 
  name, 
  lastNumbers
}: RouletteStatsModalProps) => {
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
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            Estatísticas: {name}
          </DialogTitle>
        </DialogHeader>
        
        <div className="space-y-4 p-2">
          <h3 className="text-base font-medium">Últimos Números ({lastNumbers.length})</h3>
          <div className="flex flex-wrap gap-2">
            {lastNumbers.slice(0, 20).map((num, idx) => (
              <div 
                key={idx} 
                className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${getNumberColor(num)}`}
              >
                {num}
              </div>
            ))}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default RouletteStatsModal;

