import { useState, useMemo, useEffect } from 'react';
import { Search, Wallet, Menu, MessageSquare } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Sidebar from '@/components/Sidebar';
import RouletteCard from '@/components/RouletteCard';
import { Input } from '@/components/ui/input';
import ChatUI from '@/components/ChatUI';
import { Button } from '@/components/ui/button';
import AnimatedInsights from '@/components/AnimatedInsights';
import ProfileDropdown from '@/components/ProfileDropdown';
import { 
  fetchAllRoulettes, 
  fetchRouletteLatestNumbers, 
  fetchRouletteLatestNumbersByName,
  fetchAvailableRoulettesFromNumbers
} from '@/integrations/api/rouletteService';
import { filterAllowedRoulettes } from '@/config/allowedRoulettes';
import { toast } from '@/components/ui/use-toast';
import EventService from '@/services/EventService';

interface ChatMessage {
  id: string;
  user: {
    name: string;
    avatar?: string;
    role?: string;
    isAdmin?: boolean;
    isModerator?: boolean;
  };
  message: string;
  timestamp: Date;
}

interface Roulette {
  name: string;
  lastNumbers: number[];
  wins: number;
  losses: number;
  trend: { value: number }[];
  suggestion: string;
  status: string;
}

// Gera dados de tendência baseados na taxa de vitória e derrota
const generateTrendFromWinRate = (wins: number, losses: number) => {
  const total = wins + losses;
  if (total === 0) {
    // Se não houver dados, gerar tendência aleatória
    return Array.from({ length: 20 }, () => ({ value: Math.random() * 100 }));
  }
  
  // Calcula taxa de vitória
  const winRate = wins / total;
  
  // Gera pontos de dados de tendência baseados na taxa de vitória
  return Array.from({ length: 20 }, (_, i) => {
    // Variação aleatória para simular flutuação, mas tendendo para a taxa de vitória real
    const randomVariation = (Math.random() - 0.5) * 30;
    return { value: winRate * 100 + randomVariation };
  });
};

const Index = () => {
  const [search, setSearch] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const navigate = useNavigate();
  const [roulettes, setRoulettes] = useState<Roulette[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loaded, setLoaded] = useState(false);
  
  // Inicializar o serviço de eventos quando o componente montar
  useEffect(() => {
    // Comentando a inicialização do EventService para desativar as atualizações em tempo real
    /*
    // Inicializar o EventService para começar a receber atualizações em tempo real
    const eventService = EventService.getInstance();
    
    // Limpar quando o componente desmontar
    return () => {
      // O serviço é um singleton, então não queremos destruí-lo completamente
      // apenas limpar recursos específicos deste componente se necessário
    };
    */
    
    console.log("[DEBUG] Atualizações em tempo real desativadas - EventService não inicializado");
  }, []);
  
  // Função para buscar roletas do banco de dados
  const fetchRoulettes = async () => {
    try {
      setIsLoading(true);
      
      console.log('[DEBUG] Iniciando busca de roletas no Supabase...');
      // Primeiro buscar todas as roletas disponíveis na tabela roleta_numeros
      const availableRouletteNames = await fetchAvailableRoulettesFromNumbers();
      console.log('[DEBUG] Nomes de roletas encontrados no Supabase:', availableRouletteNames);
      
      if (availableRouletteNames.length > 0) {
        // Se temos roletas do Supabase, usamos elas
        console.log('[DEBUG] Buscando objetos completos de roletas no Supabase...');
        const data = await fetchAllRoulettes();
        console.log('[DEBUG] Objetos de roletas recebidos antes do filtro:', data);
        
        // Filtrar apenas as roletas permitidas
        const allowedData = filterAllowedRoulettes(data);
        console.log('[DEBUG] IDs das roletas após filtro:', allowedData.map(r => r.id));
        console.log('[DEBUG] Nomes das roletas após filtro:', allowedData.map(r => r.nome));
        
        if (allowedData.length === 0) {
          console.warn('[DEBUG] ALERTA: O filtro de roletas permitidas removeu todas as roletas. Verifique os IDs em allowedRoulettes.ts');
        }
        
        // Para cada roleta, buscar os últimos números
        const formattedDataPromises = allowedData.map(async (item) => {
          // Buscar os últimos 20 números para cada roleta
          console.log(`[DEBUG] Buscando números para roleta '${item.nome}' (ID: ${item.id})...`);
          const lastNumbers = await fetchRouletteLatestNumbersByName(item.nome, 20);
          console.log(`[DEBUG] Números obtidos para '${item.nome}':`, lastNumbers);
          
          return {
            name: item.nome,
            lastNumbers: lastNumbers.length > 0 ? lastNumbers : (Array.isArray(item.numeros) ? item.numeros : []),
            wins: item.vitorias || 0,
            losses: item.derrotas || 0,
            trend: generateTrendFromWinRate(item.vitorias, item.derrotas),
            suggestion: item.sugestao_display || '',
            status: item.estado_estrategia || 'NEUTRAL'
          };
        });
        
        const formattedData = await Promise.all(formattedDataPromises);
        console.log('[DEBUG] Roletas formatadas finais:', formattedData.map(r => r.name));
        
        setRoulettes(formattedData);
        setLoaded(true);
        
        if (formattedData.length > 0) {
          toast({
            title: 'Dados Carregados',
            description: `${formattedData.length} roletas carregadas do Supabase`,
            variant: 'default',
          });
        } else {
          toast({
            title: 'Nenhuma roleta encontrada',
            description: 'Não foram encontradas roletas no Supabase.',
            variant: 'destructive',
          });
        }
      } else {
        // Se não há roletas no Supabase, mostramos um array vazio
        console.log('Nenhuma roleta encontrada no Supabase.');
        setRoulettes([]);
        setLoaded(true);
        
        toast({
          title: 'Nenhuma roleta encontrada',
          description: 'Não foram encontradas roletas no Supabase.',
          variant: 'destructive',
        });
      }
    } catch (error) {
      console.error('Erro ao buscar roletas do Supabase:', error);
      // Em caso de erro, mostramos um array vazio
      setRoulettes([]);
      setLoaded(true);
      
      toast({
        title: 'Erro de Conexão',
        description: 'Não foi possível conectar ao Supabase.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };
  
  // Efeito para carregar dados quando o componente montar
  useEffect(() => {
    // Buscar dados iniciais das roletas apenas uma vez quando o componente montar
    fetchRoulettes();
    
    // Não precisamos mais fazer polling, pois agora recebemos eventos em tempo real
    // O EventService já foi inicializado e cada RouletteCard se inscreveu para receber atualizações específicas
  }, []);
  
  const filteredRoulettes = roulettes.filter(roulette => 
    roulette.name.toLowerCase().includes(search.toLowerCase())
  );
  
  const topRoulettes = useMemo(() => {
    return [...roulettes].sort((a, b) => {
      const aWinRate = a.wins / (a.wins + a.losses) * 100;
      const bWinRate = b.wins / (b.wins + b.losses) * 100;
      return bWinRate - aWinRate;
    }).slice(0, 3);
  }, [roulettes]);

  // Função para depurar diretamente os dados do Supabase
  const debugSupabaseData = async () => {
    console.log("[DEPURAÇÃO] Iniciando consulta direta ao Supabase...");
    
    const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
    const SUPABASE_KEY = import.meta.env.VITE_SUPABASE_API_KEY;
    
    try {
      // Fazer uma consulta direta à tabela roleta_numeros
      const response = await fetch(
        `${SUPABASE_URL}/rest/v1/roleta_numeros?select=id,created_at,roleta_id,roleta_nome,numero&order=created_at.desc&limit=10`,
        {
          headers: {
            'apikey': SUPABASE_KEY,
            'Content-Type': 'application/json'
          }
        }
      );
      
      if (!response.ok) {
        const errorText = await response.text();
        console.error(`[ERRO] Falha na consulta direta ao Supabase: ${response.status} ${response.statusText}`, errorText);
        toast({
          title: "Erro ao acessar Supabase",
          description: `${response.status} ${response.statusText}`,
          variant: "destructive"
        });
        return;
      }
      
      const data = await response.json();
      console.log("[DEPURAÇÃO] Dados obtidos diretamente do Supabase:", data);
      
      if (Array.isArray(data) && data.length > 0) {
        toast({
          title: "Dados encontrados!",
          description: `Encontrados ${data.length} registros na tabela roleta_numeros`,
          variant: "default"
        });
        
        // Extrair nomes únicos de roletas
        const roletasUnicas = [...new Set(data.map(item => item.roleta_nome))];
        console.log("[DEPURAÇÃO] Roletas encontradas:", roletasUnicas);
        
        // Mostrar detalhes dos primeiros 5 registros
        console.log("[DEPURAÇÃO] Primeiros registros:");
        for (let i = 0; i < Math.min(5, data.length); i++) {
          console.log(`[${i+1}] ID: ${data[i].id}, Roleta: ${data[i].roleta_nome}, Número: ${data[i].numero}, Data: ${data[i].created_at}`);
        }
      } else {
        toast({
          title: "Nenhum dado encontrado",
          description: "A tabela roleta_numeros parece estar vazia.",
          variant: "destructive"
        });
      }
    } catch (error) {
      console.error("[ERRO] Falha ao consultar diretamente o Supabase:", error);
      toast({
        title: "Erro na consulta",
        description: error instanceof Error ? error.message : String(error),
        variant: "destructive"
      });
    }
  };

  return (
    <div className="min-h-screen flex bg-vegas-black">
      {/* Desktop Sidebar */}
      <Sidebar />
      
      {/* Mobile Sidebar (drawer) */}
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} isMobile={true} />
      
      <div className="flex-1 relative">
        {/* Mobile Header */}
        <div className="mobile-header">
          <button 
            className="p-2"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={24} className="text-[#00ff00]" />
          </button>
          
          <span className="text-white text-xl font-bold">RunCash</span>
          
          <button 
            className="p-2"
            onClick={() => setChatOpen(true)}
          >
            <MessageSquare size={24} className="text-[#00ff00]" />
          </button>
        </div>
        
        {/* Desktop Header */}
        <div className="hidden md:flex fixed top-0 left-0 right-0 md:left-64 md:right-80 z-40 h-[70px] items-center justify-between px-4 border-b border-[#33333359] bg-[#100f13]">
          <div className="flex items-center gap-2">
            <span className="text-white text-2xl font-bold">RunCash</span>
            <div className="relative flex items-center ml-4 max-w-[180px]">
              <Search size={14} className="absolute left-2 text-gray-400" />
              <Input 
                type="text" 
                placeholder="Pesquisar roleta..." 
                className="h-8 pl-7 py-1 pr-2 text-xs bg-[#1A191F] border-none rounded-full text-white focus-visible:ring-0 focus-visible:ring-offset-0" 
                value={search} 
                onChange={e => setSearch(e.target.value)} 
              />
            </div>
          </div>
          
          <AnimatedInsights />
          
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-[#1A191F] rounded-full py-1 px-3">
              <span className="h-5 w-5 bg-vegas-blue rounded-full flex items-center justify-center">
                <span className="text-[10px] text-white">R$</span>
              </span>
              <span className="text-white text-xs">1.346,34</span>
              <Wallet size={14} className="text-gray-400" />
            </div>
            
            <Button variant="default" size="sm" className="h-8 text-black font-medium bg-gradient-to-b from-[#00ff00] to-[#00ff00] hover:from-[#00ff00]/90 hover:to-[#00ff00]/90">
              <Wallet size={14} className="mr-1" /> Saldo
            </Button>
            
            <ProfileDropdown />
          </div>
        </div>
        
        {/* Mobile Search Bar */}
        <div className="md:hidden px-4 pt-20 pb-2">
          <div className="relative flex items-center w-full">
            <Search size={16} className="absolute left-3 text-gray-400" />
            <Input 
              type="text" 
              placeholder="Pesquisar roleta..." 
              className="w-full pl-9 py-2 pr-3 text-sm bg-[#1A191F] border-none rounded-full text-white focus-visible:ring-0 focus-visible:ring-offset-0" 
              value={search} 
              onChange={e => setSearch(e.target.value)} 
            />
          </div>
        </div>
        
        {/* Mobile User Info */}
        <div className="md:hidden flex justify-between items-center px-4 py-3">
          <ProfileDropdown />
          
          <Button variant="default" size="sm" className="h-8 text-black font-medium bg-gradient-to-b from-[#00ff00] to-[#00ff00] hover:from-[#00ff00]/90 hover:to-[#00ff00]/90">
            <Wallet size={14} className="mr-1" /> Saldo
          </Button>
        </div>
        
        {/* Mobile Insights */}
        <div className="md:hidden px-4 py-2">
          <div className="bg-[#1A191F]/50 rounded-lg p-3">
            <AnimatedInsights />
          </div>
        </div>
        
        <main className="pt-4 md:pt-[70px] pb-8 px-4 md:px-6 md:pl-[280px] md:pr-[340px] w-full min-h-screen bg-[#100f13]">
          {isLoading ? (
            <div className="flex justify-center items-center h-[200px]">
              <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-vegas-gold"></div>
            </div>
          ) : (
            <>
              <div className="mb-6 bg-gradient-to-r from-vegas-gold to-yellow-500 p-4 rounded-lg">
                <h3 className="text-black font-bold mb-2">Atualize para o Plano Premium</h3>
                <p className="text-black/80 mb-3">Acesse estatísticas em tempo real e muito mais!</p>
                <button 
                  className="bg-black text-white px-4 py-2 rounded-md text-sm"
                  onClick={() => navigate('/planos')}
                >
                  Ver Planos
                </button>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6 mt-2 md:mt-6">
                {filteredRoulettes.map((roulette, index) => (
                  <RouletteCard key={index} {...roulette} />
                ))}
              </div>
            </>
          )}
          
          {/* Mobile Footer Space (to avoid content being hidden behind fixed elements) */}
          <div className="h-16 md:h-0"></div>
        </main>
      </div>
      
      {/* Desktop Chat */}
      <ChatUI />
      
      {/* Mobile Chat (drawer) */}
      <ChatUI isOpen={chatOpen} onClose={() => setChatOpen(false)} isMobile={true} />
      
      {/* Loading indicator */}
      {isLoading && (
        <div className="fixed top-4 right-4 bg-[#00ff00]/10 text-[#00ff00] px-4 py-2 rounded-md border border-[#00ff00]/20 z-50">
          Atualizando dados do Supabase...
        </div>
      )}
      
      {/* Botão de depuração - posicione onde for mais conveniente */}
      <div className="fixed bottom-4 right-4 z-50">
        <Button
          onClick={debugSupabaseData}
          className="bg-purple-600 hover:bg-purple-700 text-white px-4 py-2 rounded-md"
        >
          Depurar Supabase
        </Button>
      </div>
    </div>
  );
};

export default Index;
