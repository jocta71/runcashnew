import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";
import { ChartBar, X, TrendingUp, BarChart, ArrowDown, ArrowUp, PercentIcon } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart as RechartsBarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Bar,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";
import { useState, useEffect } from "react";
import { fetchRouletteById } from "@/integrations/api/rouletteService";

interface RouletteStatsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  lastNumbers: number[];
  wins: number;
  losses: number;
  trend: { value: number }[];
  rouletteId?: string;
}

// Generate frequency data for numbers
const generateFrequencyData = (numbers: number[]) => {
  const frequency: Record<number, number> = {};
  
  // Initialize all roulette numbers (0-36)
  for (let i = 0; i <= 36; i++) {
    frequency[i] = 0;
  }
  
  // Count occurrences
  numbers.forEach(num => {
    frequency[num] += 1;
  });
  
  // Convert to array for recharts
  return Object.entries(frequency).map(([number, count]) => ({
    number: Number(number),
    frequency: count,
  }));
};

// Calculate hot and cold numbers
const getHotColdNumbers = (frequencyData: {number: number, frequency: number}[]) => {
  const sorted = [...frequencyData].sort((a, b) => b.frequency - a.frequency);
  return {
    hot: sorted.slice(0, 5),  // 5 most frequent
    cold: sorted.slice(-5).reverse()  // 5 least frequent
  };
};

// Generate pie chart data for number groups
const generateGroupDistribution = (numbers: number[]) => {
  const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
  const groups = [
    { name: "Vermelhos", value: 0, color: "#ef4444" },
    { name: "Pretos", value: 0, color: "#111827" },
    { name: "Zero", value: 0, color: "#059669" },
  ];
  
  numbers.forEach(num => {
    if (num === 0) {
      groups[2].value += 1;
    } else if (redNumbers.includes(num)) {
      groups[0].value += 1;
    } else {
      groups[1].value += 1;
    }
  });
  
  return groups;
};

// Determine color for a roulette number
const getRouletteNumberColor = (num: number) => {
  if (num === 0) return "bg-vegas-green text-black";
  
  // Red numbers
  const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
  
  if (redNumbers.includes(num)) {
    return "bg-red-600 text-white";
  } else {
    return "bg-black text-white";
  }
};

const RouletteStatsModal = ({ 
  open, 
  onOpenChange, 
  name, 
  lastNumbers, 
  wins, 
  losses, 
  trend,
  rouletteId
}: RouletteStatsModalProps) => {
  const [historicalNumbers, setHistoricalNumbers] = useState<number[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const fetchHistoricalData = async () => {
      if (open && name) {
        setIsLoading(true);
        try {
          const roulettes = await fetchRouletteById(rouletteId || '');
          if (roulettes && roulettes.numeros) {
            // Usar todos os números disponíveis da roleta
            setHistoricalNumbers(roulettes.numeros);
          } else {
            // Fallback para os últimos números se não conseguir buscar o histórico completo
            setHistoricalNumbers(lastNumbers);
          }
        } catch (error) {
          console.error('Erro ao buscar histórico de números:', error);
          // Fallback para os últimos números em caso de erro
          setHistoricalNumbers(lastNumbers);
        } finally {
          setIsLoading(false);
        }
      }
    };

    fetchHistoricalData();
  }, [open, name, rouletteId, lastNumbers]);

  const frequencyData = generateFrequencyData(historicalNumbers);
  const { hot, cold } = getHotColdNumbers(frequencyData);
  const pieData = generateGroupDistribution(historicalNumbers);
  
  const winRate = (wins / (wins + losses)) * 100;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto bg-vegas-black border-vegas-gold">
        <DialogHeader>
          <DialogTitle className="text-vegas-gold flex items-center text-xl">
            <BarChart className="mr-2" /> Estatísticas da {name}
          </DialogTitle>
          <DialogDescription>
            Análise detalhada dos {historicalNumbers.length} números extraídos e tendências
          </DialogDescription>
        </DialogHeader>
        
        <DialogClose className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground text-vegas-gold">
          <X className="h-4 w-4" />
          <span className="sr-only">Fechar</span>
        </DialogClose>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Historical Numbers Section */}
          <div className="glass-card p-4 space-y-4">
            <h3 className="text-lg font-semibold flex items-center">
              <TrendingUp size={20} className="text-vegas-gold mr-2" /> Histórico de Números ({historicalNumbers.length})
            </h3>
            <div className="grid grid-cols-10 gap-2">
              {historicalNumbers.slice(0, 120).map((num, i) => (
                <div
                  key={i}
                  className={`w-8 h-8 rounded-full ${getRouletteNumberColor(num)} flex items-center justify-center text-sm font-medium`}
                >
                  {num}
                </div>
              ))}
            </div>
          </div>

          {/* Win Rate Chart */}
          <div className="glass-card p-4 space-y-4">
            <h3 className="text-lg font-semibold flex items-center">
              <PercentIcon size={20} className="text-vegas-gold mr-2" /> Taxa de Vitória
            </h3>
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={[
                      { name: "Vitórias", value: wins },
                      { name: "Derrotas", value: losses }
                    ]}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    fill="#3BFFA1"
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    <Cell key="wins" fill="#3BFFA1" />
                    <Cell key="losses" fill="#ef4444" />
                  </Pie>
                  <Legend />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          {/* Frequency Chart */}
          <div className="glass-card p-4 space-y-4">
            <h3 className="text-lg font-semibold flex items-center">
              <ChartBar size={20} className="text-vegas-gold mr-2" /> Frequência de Números
            </h3>
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <RechartsBarChart data={frequencyData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                  <XAxis dataKey="number" stroke="#ccc" />
                  <YAxis stroke="#ccc" />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#222', borderColor: '#3BFFA1' }} 
                    labelStyle={{ color: '#3BFFA1' }}
                  />
                  <Bar dataKey="frequency" fill="#3BFFA1" />
                </RechartsBarChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          {/* Distribution Pie Chart */}
          <div className="glass-card p-4 space-y-4">
            <h3 className="text-lg font-semibold flex items-center">
              <ChartBar size={20} className="text-vegas-gold mr-2" /> Distribuição por Cor
            </h3>
            <div className="h-60">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    fill="#3BFFA1"
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Legend />
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          
          {/* Hot & Cold Numbers */}
          <div className="glass-card p-4 space-y-4 col-span-1 lg:col-span-2">
            <h3 className="text-lg font-semibold">Números Quentes & Frios</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-3 bg-vegas-darkgray rounded-lg">
                <h4 className="text-md font-semibold flex items-center text-red-500 mb-2">
                  <ArrowUp size={16} className="mr-1" /> Números Quentes (Mais Frequentes)
                </h4>
                <div className="flex flex-wrap gap-2">
                  {hot.map((item, i) => (
                    <div key={i} className="flex items-center space-x-1">
                      <div className={`w-8 h-8 rounded-full ${getRouletteNumberColor(item.number)} flex items-center justify-center text-sm font-medium`}>
                        {item.number}
                      </div>
                      <span className="text-vegas-gold">({item.frequency}x)</span>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="p-3 bg-vegas-darkgray rounded-lg">
                <h4 className="text-md font-semibold flex items-center text-blue-500 mb-2">
                  <ArrowDown size={16} className="mr-1" /> Números Frios (Menos Frequentes)
                </h4>
                <div className="flex flex-wrap gap-2">
                  {cold.map((item, i) => (
                    <div key={i} className="flex items-center space-x-1">
                      <div className={`w-8 h-8 rounded-full ${getRouletteNumberColor(item.number)} flex items-center justify-center text-sm font-medium`}>
                        {item.number}
                      </div>
                      <span className="text-vegas-gold">({item.frequency}x)</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
};

export default RouletteStatsModal;
