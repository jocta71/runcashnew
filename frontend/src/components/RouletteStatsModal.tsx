import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog";
import { ChartBar, X, TrendingUp, BarChart, ArrowDown, ArrowUp, PercentIcon, Clock, RotateCw, Zap } from "lucide-react";
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
import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { fetchRouletteLatestNumbersByName } from '@/integrations/api/rouletteService';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface RouletteStatsModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  name: string;
  lastNumbers: number[];
  wins: number;
  losses: number;
  trend: { value: number }[];
}

// Função para buscar números do banco para uma roleta específica
const fetchRouletteHistoricalNumbers = async (rouletteName: string) => {
  try {
    console.log(`[${new Date().toLocaleTimeString()}] Buscando histórico para ${rouletteName}...`);
    
    // Primeiro obtemos o ID da roleta
    const idResponse = await fetch(
      `https://evzqzghxuttctbxgohpx.supabase.co/rest/v1/roletas?nome=eq.${encodeURIComponent(rouletteName)}&select=id`,
      {
        headers: {
          'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ',
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (!idResponse.ok) {
      throw new Error(`Erro ao buscar ID da roleta: ${idResponse.statusText}`);
    }
    
    const idData = await idResponse.json();
    if (!idData || idData.length === 0) {
      console.log(`[${new Date().toLocaleTimeString()}] Roleta não encontrada: ${rouletteName}`);
      return [];
    }
    
    const roletaId = idData[0].id;
    console.log(`[${new Date().toLocaleTimeString()}] ID da roleta ${rouletteName}: ${roletaId}`);
    
    // Agora buscamos até 100 números da tabela roleta_numeros
    const response = await fetch(
      `https://evzqzghxuttctbxgohpx.supabase.co/rest/v1/roleta_numeros?roleta_id=eq.${roletaId}&select=numero,created_at&order=created_at.desc&limit=100`,
      {
        headers: {
          'apikey': 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ',
          'Content-Type': 'application/json'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error('Falha ao buscar dados históricos');
    }
    
    const data = await response.json();
    console.log(`[${new Date().toLocaleTimeString()}] Resposta do Supabase para ${rouletteName}:`, data);
    
    if (data && Array.isArray(data) && data.length > 0) {
      console.log(`[${new Date().toLocaleTimeString()}] Dados históricos encontrados para ${rouletteName}: ${data.length} números`);
      
      // Extrair apenas os números e converter para inteiros se necessário
      const validNumbers = data
        .map(item => typeof item.numero === 'string' ? parseInt(item.numero, 10) : Number(item.numero))
        .filter(num => !isNaN(num) && num >= 0 && num <= 36);
      
      // Invertemos a ordem para ter do mais antigo para o mais recente
      const reversedNumbers = validNumbers.reverse();
      
      console.log(`[${new Date().toLocaleTimeString()}] Números válidos para ${rouletteName}: ${reversedNumbers.length}`);
      
      return reversedNumbers;
    } else {
      console.log(`[${new Date().toLocaleTimeString()}] Nenhum dado encontrado para ${rouletteName}`);
    }
    
    return [];
  } catch (error) {
    console.error(`[${new Date().toLocaleTimeString()}] Erro ao buscar números históricos:`, error);
    return [];
  }
};

// Fallback para quando não há dados suficientes
const generateHistoricalNumbers = () => {
  const numbers = [];
  for (let i = 0; i < 120; i++) {
    numbers.push(Math.floor(Math.random() * 37)); // 0-36 for roulette
  }
  return numbers;
};

// Generate frequency data for numbers
const generateFrequencyData = (numbers: number[]) => {
  const frequency: Record<number, number> = {};
  
  // Initialize all roulette numbers (0-36)
  for (let i = 0; i <= 36; i++) {
    frequency[i] = 0;
  }
  
  // Count frequency of each number
  numbers.forEach(num => {
    if (frequency[num] !== undefined) {
      frequency[num]++;
    }
  });
  
  // Convert to array format needed for charts
  return Object.keys(frequency).map(key => ({
    number: parseInt(key),
    frequency: frequency[parseInt(key)]
  })).sort((a, b) => a.number - b.number);
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

// Gerar dados de média de cores por hora
const generateColorHourlyStats = (numbers: number[]) => {
  const redNumbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
  const total = numbers.length;
  
  // Contar números por cor
  const redCount = numbers.filter(num => redNumbers.includes(num)).length;
  const blackCount = numbers.filter(num => num !== 0 && !redNumbers.includes(num)).length;
  const zeroCount = numbers.filter(num => num === 0).length;
  
  // Calcular média por hora (assumindo que temos dados de uma hora)
  // Para um cenário real, usaríamos dados com timestamps
  const redAverage = parseFloat((redCount / (total / 60)).toFixed(2));
  const blackAverage = parseFloat((blackCount / (total / 60)).toFixed(2));
  const zeroAverage = parseFloat((zeroCount / (total / 60)).toFixed(2));
  
  return [
    {
      name: "Média de vermelhos por hora",
      value: redAverage,
      color: "#ef4444",
      total: redCount,
      percentage: parseFloat(((redCount / total) * 100).toFixed(2))
    },
    {
      name: "Média de pretos por hora",
      value: blackAverage,
      color: "#111827",
      total: blackCount,
      percentage: parseFloat(((blackCount / total) * 100).toFixed(2))
    },
    {
      name: "Média de brancos por hora",
      value: zeroAverage,
      color: "#059669",
      total: zeroCount,
      percentage: parseFloat(((zeroCount / total) * 100).toFixed(2))
    }
  ];
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
  trend 
}: RouletteStatsModalProps) => {
  const [historicalNumbers, setHistoricalNumbers] = useState<number[]>([]);
  const [historicalTimestamps, setHistoricalTimestamps] = useState<string[]>([]);
  const [frequencyData, setFrequencyData] = useState<any[]>([]);
  const [groupDistribution, setGroupDistribution] = useState<any[]>([]);
  const [colorDistribution, setColorDistribution] = useState<any[]>([]);
  const [hotColdNumbers, setHotColdNumbers] = useState<any>({ hot: [], cold: [] });
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");
  const [sequenceDetection, setSequenceDetection] = useState<{
    colorSequences: {color: string, count: number}[],
    evenOddSequences: {type: string, count: number}[],
    dozenSequences: {dozen: string, count: number}[],
    halfSequences: {half: string, count: number}[]
  }>({
    colorSequences: [],
    evenOddSequences: [],
    dozenSequences: [],
    halfSequences: []
  });
  
  useEffect(() => {
    if (open) {
      loadHistoricalData();
    }
  }, [open, name]);

  const loadHistoricalData = async () => {
    setIsLoading(true);
    try {
      // Buscar até 1000 números para análise estatística mais precisa
      const result = await fetchRouletteLatestNumbersByName(name, 1000, true);
      
      if (result && result.numbers && result.numbers.length > 0) {
        const numbers = result.numbers;
        setHistoricalNumbers(numbers);
        
        if (result.timestamps) {
          setHistoricalTimestamps(result.timestamps);
        }
        
        // Calcular frequências
        const freqData = generateFrequencyData(numbers);
        setFrequencyData(freqData);
        
        // Definir hot/cold
        setHotColdNumbers(getHotColdNumbers(freqData));
        
        // Calcular distribuição por grupos
        setGroupDistribution(generateGroupDistribution(numbers));
        
        // Calcular distribuição por cores
        setColorDistribution(generateColorDistribution(numbers));
        
        // Detectar sequências
        detectSequences(numbers);
      } else {
        // Usar os números disponíveis no componente se não conseguir buscar do servidor
        setHistoricalNumbers(lastNumbers);
        // Calcular com os dados limitados disponíveis
        const freqData = generateFrequencyData(lastNumbers);
        setFrequencyData(freqData);
        setHotColdNumbers(getHotColdNumbers(freqData));
        setGroupDistribution(generateGroupDistribution(lastNumbers));
        setColorDistribution(generateColorDistribution(lastNumbers));
        detectSequences(lastNumbers);
      }
    } catch (error) {
      console.error("Erro ao carregar dados históricos:", error);
      // Usar os números disponíveis localmente em caso de erro
      setHistoricalNumbers(lastNumbers);
      const freqData = generateFrequencyData(lastNumbers);
      setFrequencyData(freqData);
      setHotColdNumbers(getHotColdNumbers(freqData));
      setGroupDistribution(generateGroupDistribution(lastNumbers));
      setColorDistribution(generateColorDistribution(lastNumbers));
      detectSequences(lastNumbers);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Função para detectar sequências nos números
  const detectSequences = (numbers: number[]) => {
    if (!numbers || numbers.length < 10) return;
    
    const getColor = (num: number) => {
      if (num === 0) return 'green';
      return [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num) ? 'red' : 'black';
    };
    
    const getEvenOdd = (num: number) => {
      if (num === 0) return 'zero';
      return num % 2 === 0 ? 'even' : 'odd';
    };
    
    const getDozen = (num: number) => {
      if (num === 0) return 'zero';
      if (num <= 12) return 'first';
      if (num <= 24) return 'second';
      return 'third';
    };
    
    const getHalf = (num: number) => {
      if (num === 0) return 'zero';
      return num <= 18 ? 'low' : 'high';
    };
    
    // Encontrar sequências de cores
    const colorSeqs: Record<string, number> = {};
    const evenOddSeqs: Record<string, number> = {};
    const dozenSeqs: Record<string, number> = {};
    const halfSeqs: Record<string, number> = {};
    
    let currentColorSeq = getColor(numbers[0]);
    let currentEvenOddSeq = getEvenOdd(numbers[0]);
    let currentDozenSeq = getDozen(numbers[0]);
    let currentHalfSeq = getHalf(numbers[0]);
    
    let colorCount = 1;
    let evenOddCount = 1;
    let dozenCount = 1;
    let halfCount = 1;
    
    for (let i = 1; i < numbers.length; i++) {
      const num = numbers[i];
      const color = getColor(num);
      const evenOdd = getEvenOdd(num);
      const dozen = getDozen(num);
      const half = getHalf(num);
      
      // Verificar sequências de cor
      if (color === currentColorSeq) {
        colorCount++;
      } else {
        if (colorCount >= 3) {
          const key = `${currentColorSeq}-${colorCount}`;
          colorSeqs[key] = (colorSeqs[key] || 0) + 1;
        }
        currentColorSeq = color;
        colorCount = 1;
      }
      
      // Verificar sequências de par/ímpar
      if (evenOdd === currentEvenOddSeq) {
        evenOddCount++;
      } else {
        if (evenOddCount >= 3) {
          const key = `${currentEvenOddSeq}-${evenOddCount}`;
          evenOddSeqs[key] = (evenOddSeqs[key] || 0) + 1;
        }
        currentEvenOddSeq = evenOdd;
        evenOddCount = 1;
      }
      
      // Verificar sequências de dúzias
      if (dozen === currentDozenSeq) {
        dozenCount++;
      } else {
        if (dozenCount >= 3) {
          const key = `${currentDozenSeq}-${dozenCount}`;
          dozenSeqs[key] = (dozenSeqs[key] || 0) + 1;
        }
        currentDozenSeq = dozen;
        dozenCount = 1;
      }
      
      // Verificar sequências de metades
      if (half === currentHalfSeq) {
        halfCount++;
      } else {
        if (halfCount >= 3) {
          const key = `${currentHalfSeq}-${halfCount}`;
          halfSeqs[key] = (halfSeqs[key] || 0) + 1;
        }
        currentHalfSeq = half;
        halfCount = 1;
      }
    }
    
    // Processar os resultados
    const colorSequences = Object.entries(colorSeqs)
      .map(([key, count]) => {
        const [color, seqLength] = key.split('-');
        return { color, count: parseInt(seqLength) };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
      
    const evenOddSequences = Object.entries(evenOddSeqs)
      .map(([key, count]) => {
        const [type, seqLength] = key.split('-');
        return { type, count: parseInt(seqLength) };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
      
    const dozenSequences = Object.entries(dozenSeqs)
      .map(([key, count]) => {
        const [dozen, seqLength] = key.split('-');
        return { dozen, count: parseInt(seqLength) };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
      
    const halfSequences = Object.entries(halfSeqs)
      .map(([key, count]) => {
        const [half, seqLength] = key.split('-');
        return { half, count: parseInt(seqLength) };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
    
    setSequenceDetection({
      colorSequences,
      evenOddSequences,
      dozenSequences,
      halfSequences
    });
  };
  
  const generateColorDistribution = (numbers: number[]) => {
    if (!numbers || numbers.length === 0) return [];
    
    const redCount = numbers.filter(num => 
      [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num)
    ).length;
    
    const blackCount = numbers.filter(num => 
      [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35].includes(num)
    ).length;
    
    const greenCount = numbers.filter(num => num === 0).length;
    
    return [
      { name: 'Vermelho', value: redCount, color: '#e11d48' },
      { name: 'Preto', value: blackCount, color: '#27272a' },
      { name: 'Verde', value: greenCount, color: '#16a34a' }
    ];
  };
  
  const formatTimestamp = (timestamp: string) => {
    try {
      return format(new Date(timestamp), 'dd/MM/yyyy HH:mm:ss', {locale: ptBR});
    } catch (e) {
      return timestamp;
    }
  };
  
  const getSequenceLabel = (type: string, value: string) => {
    if (type === 'color') {
      if (value === 'red') return 'Vermelho';
      if (value === 'black') return 'Preto';
      return 'Verde';
    }
    
    if (type === 'evenOdd') {
      if (value === 'even') return 'Pares';
      if (value === 'odd') return 'Ímpares';
      return 'Zero';
    }
    
    if (type === 'dozen') {
      if (value === 'first') return '1ª Dúzia';
      if (value === 'second') return '2ª Dúzia';
      if (value === 'third') return '3ª Dúzia';
      return 'Zero';
    }
    
    if (type === 'half') {
      if (value === 'low') return 'Baixos (1-18)';
      if (value === 'high') return 'Altos (19-36)';
      return 'Zero';
    }
    
    return value;
  };
  
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex justify-between items-center">
            <DialogTitle className="text-xl flex items-center">
              <ChartBar className="mr-2 h-5 w-5" />
              Análise Detalhada: {name}
            </DialogTitle>
            <DialogClose className="w-8 h-8 rounded-full flex items-center justify-center">
              <X className="h-4 w-4" />
            </DialogClose>
          </div>
          <DialogDescription>
            Análise com base nos últimos {historicalNumbers.length} números sorteados
          </DialogDescription>
        </DialogHeader>
        
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="w-full justify-start mb-6">
            <TabsTrigger value="overview">Visão Geral</TabsTrigger>
            <TabsTrigger value="numbers">Números</TabsTrigger>
            <TabsTrigger value="sequences">Sequências</TabsTrigger>
            <TabsTrigger value="timeline">Linha do Tempo</TabsTrigger>
          </TabsList>
          
          <TabsContent value="overview" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Distribuição de Cores</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={colorDistribution}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="value"
                          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                        >
                          {colorDistribution.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => [`${value} números`, '']} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Números Mais Frequentes</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <RechartsBarChart
                        data={frequencyData.slice(0, 10)}
                        layout="vertical"
                        margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" />
                        <YAxis dataKey="number" type="category" />
                        <Tooltip />
                        <Bar dataKey="frequency" fill="#4f46e5" />
                      </RechartsBarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Números Quentes</CardTitle>
                  <CardDescription>Números que mais saíram recentemente</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {hotColdNumbers.hot.map((item: any) => (
                      <Badge 
                        key={item.number} 
                        variant="outline" 
                        className={`px-2 py-1 ${
                          item.number === 0 ? 'bg-green-100 border-green-300 text-green-600' : 
                          [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(item.number) ? 
                            'bg-red-100 border-red-300 text-red-600' : 
                            'bg-gray-100 border-gray-300 text-gray-600'
                        }`}
                      >
                        {item.number} ({item.frequency}x)
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Números Frios</CardTitle>
                  <CardDescription>Números que menos saíram recentemente</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {hotColdNumbers.cold.map((item: any) => (
                      <Badge 
                        key={item.number} 
                        variant="outline" 
                        className={`px-2 py-1 ${
                          item.number === 0 ? 'bg-green-100 border-green-300 text-green-600' : 
                          [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(item.number) ? 
                            'bg-red-100 border-red-300 text-red-600' : 
                            'bg-gray-100 border-gray-300 text-gray-600'
                        }`}
                      >
                        {item.number} ({item.frequency}x)
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          <TabsContent value="numbers" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Histórico de Números</CardTitle>
                <CardDescription>
                  Últimos {Math.min(historicalNumbers.length, 50)} números em ordem cronológica
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b">
                        <th className="text-left py-2">#</th>
                        <th className="text-left py-2">Número</th>
                        <th className="text-left py-2">Cor</th>
                        <th className="text-left py-2">Par/Ímpar</th>
                        <th className="text-left py-2">Dúzia</th>
                        <th className="text-left py-2">Data/Hora</th>
                      </tr>
                    </thead>
                    <tbody>
                      {historicalNumbers.slice(0, 50).map((num, idx) => (
                        <tr key={idx} className={idx % 2 === 0 ? 'bg-gray-50 dark:bg-gray-800' : ''}>
                          <td className="py-2">{idx + 1}</td>
                          <td className="py-2">
                            <span 
                              className={`inline-flex items-center justify-center w-7 h-7 rounded-full text-white 
                                ${num === 0 
                                  ? 'bg-green-600' 
                                  : [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num) 
                                    ? 'bg-red-600' 
                                    : 'bg-gray-900'
                                }`}
                            >
                              {num}
                            </span>
                          </td>
                          <td className="py-2">
                            {num === 0 
                              ? 'Verde' 
                              : [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num) 
                                ? 'Vermelho' 
                                : 'Preto'
                            }
                          </td>
                          <td className="py-2">{num === 0 ? 'Zero' : num % 2 === 0 ? 'Par' : 'Ímpar'}</td>
                          <td className="py-2">
                            {num === 0 
                              ? 'Zero' 
                              : num <= 12 
                                ? '1ª (1-12)' 
                                : num <= 24 
                                  ? '2ª (13-24)' 
                                  : '3ª (25-36)'
                            }
                          </td>
                          <td className="py-2">
                            {historicalTimestamps && historicalTimestamps[idx] 
                              ? formatTimestamp(historicalTimestamps[idx])
                              : '-'
                            }
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          <TabsContent value="sequences" className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center">
                    <RotateCw className="h-4 w-4 mr-2" />
                    Sequências de Cores
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {sequenceDetection.colorSequences.length > 0 ? (
                      sequenceDetection.colorSequences.map((seq, idx) => (
                        <div key={idx} className="flex items-center justify-between">
                          <div className="flex items-center">
                            <div 
                              className={`w-4 h-4 rounded-full mr-2 ${
                                seq.color === 'red' ? 'bg-red-600' : 
                                seq.color === 'black' ? 'bg-gray-900' : 'bg-green-600'
                              }`}
                            />
                            <span>{getSequenceLabel('color', seq.color)}</span>
                          </div>
                          <Badge>{seq.count}x seguidos</Badge>
                        </div>
                      ))
                    ) : (
                      <p className="text-gray-500 text-sm">Nenhuma sequência significativa detectada</p>
                    )}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center">
                    <RotateCw className="h-4 w-4 mr-2" />
                    Sequências Par/Ímpar
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {sequenceDetection.evenOddSequences.length > 0 ? (
                      sequenceDetection.evenOddSequences.map((seq, idx) => (
                        <div key={idx} className="flex items-center justify-between">
                          <span>{getSequenceLabel('evenOdd', seq.type)}</span>
                          <Badge>{seq.count}x seguidos</Badge>
                        </div>
                      ))
                    ) : (
                      <p className="text-gray-500 text-sm">Nenhuma sequência significativa detectada</p>
                    )}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center">
                    <RotateCw className="h-4 w-4 mr-2" />
                    Sequências de Dúzias
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {sequenceDetection.dozenSequences.length > 0 ? (
                      sequenceDetection.dozenSequences.map((seq, idx) => (
                        <div key={idx} className="flex items-center justify-between">
                          <span>{getSequenceLabel('dozen', seq.dozen)}</span>
                          <Badge>{seq.count}x seguidos</Badge>
                        </div>
                      ))
                    ) : (
                      <p className="text-gray-500 text-sm">Nenhuma sequência significativa detectada</p>
                    )}
                  </div>
                </CardContent>
              </Card>
              
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center">
                    <RotateCw className="h-4 w-4 mr-2" />
                    Sequências Altos/Baixos
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {sequenceDetection.halfSequences.length > 0 ? (
                      sequenceDetection.halfSequences.map((seq, idx) => (
                        <div key={idx} className="flex items-center justify-between">
                          <span>{getSequenceLabel('half', seq.half)}</span>
                          <Badge>{seq.count}x seguidos</Badge>
                        </div>
                      ))
                    ) : (
                      <p className="text-gray-500 text-sm">Nenhuma sequência significativa detectada</p>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
          
          <TabsContent value="timeline" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Linha do Tempo dos Números</CardTitle>
                <CardDescription>
                  Visualização dos números por ordem cronológica
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-5">
                  {historicalNumbers.slice(0, 25).map((num, idx) => (
                    <div key={idx} className="flex items-start relative">
                      <div className="z-10">
                        <div 
                          className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-medium ${
                            num === 0 
                              ? 'bg-green-600' 
                              : [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num) 
                                ? 'bg-red-600' 
                                : 'bg-gray-900'
                          }`}
                        >
                          {num}
                        </div>
                      </div>
                      
                      {idx < historicalNumbers.length - 1 && (
                        <div className="absolute left-4 top-8 w-0.5 h-5 bg-gray-200 dark:bg-gray-700" />
                      )}
                      
                      <div className="ml-4">
                        <div className="text-sm font-medium">
                          {num === 0 
                            ? 'Zero (Verde)' 
                            : [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36].includes(num) 
                              ? `${num} (Vermelho)` 
                              : `${num} (Preto)`
                          }
                        </div>
                        
                        <div className="text-xs text-gray-500 flex items-center">
                          <Clock className="h-3 w-3 mr-1" />
                          {historicalTimestamps && historicalTimestamps[idx] 
                            ? formatTimestamp(historicalTimestamps[idx])
                            : 'Horário desconhecido'
                          }
                        </div>
                        
                        <div className="text-xs text-gray-500 mt-1">
                          {num === 0 ? 'Zero' : num % 2 === 0 ? 'Par' : 'Ímpar'} • 
                          {num === 0 
                            ? ' Zero' 
                            : num <= 12 
                              ? ' 1ª Dúzia' 
                              : num <= 24 
                                ? ' 2ª Dúzia' 
                                : ' 3ª Dúzia'
                          } • 
                          {num === 0 
                            ? ' Zero' 
                            : num <= 18 
                              ? ' Baixo (1-18)' 
                              : ' Alto (19-36)'
                          }
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </DialogContent>
    </Dialog>
  );
};

export default RouletteStatsModal;

