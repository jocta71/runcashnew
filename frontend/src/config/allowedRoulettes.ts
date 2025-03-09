/**
 * Configuração dinâmica de roletas permitidas para exibição no frontend
 */

// Configuração do Supabase
const SUPABASE_URL = "https://evzqzghxuttctbxgohpx.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ";

// Lista inicial de roletas IDs permitidas (usada como fallback)
export const ROLETAS_PERMITIDAS_INICIAL = [
  "2010016",  // Immersive Roulette
  "2380335",  // Brazilian Mega Roulette
  "2010065",  // Bucharest Auto-Roulette
  "2010096",  // Speed Auto Roulette
  "2010017",  // Auto-Roulette
  "2010098",  // Auto-Roulette VIP
];

// Lista dinâmica que será preenchida em tempo de execução
let roletasPermitidas: string[] = [...ROLETAS_PERMITIDAS_INICIAL];
let roletasNomePermitidas: string[] = [];
let listaAtualizada = false;

/**
 * Busca as roletas disponíveis do Supabase e atualiza a lista de permitidas
 * @returns Promise com a lista de roletas permitidas
 */
export const atualizarRoletasPermitidas = async (): Promise<string[]> => {
  try {
    console.log('[AllowedRoulettes] Buscando roletas disponíveis no Supabase...');
    
    // Buscar diretamente do Supabase com seleção distinta dos nomes de roletas
    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/roleta_numeros?select=roleta_nome,roleta_id&order=roleta_nome`,
      {
        headers: {
          'apikey': SUPABASE_KEY,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache, no-store',
          'Prefer': 'distinct=true'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(`Erro ao buscar roletas disponíveis: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[AllowedRoulettes] Encontradas ${data.length} roletas únicas na tabela roleta_numeros.`);
    
    // Extrair IDs e nomes das roletas
    const uniqueIds = new Set<string>();
    const uniqueNames = new Set<string>();
    
    data.forEach(item => {
      if (item.roleta_id) uniqueIds.add(item.roleta_id);
      if (item.roleta_nome) uniqueNames.add(item.roleta_nome);
    });
    
    // Atualizar as listas dinâmicas
    roletasPermitidas = [...uniqueIds];
    roletasNomePermitidas = [...uniqueNames];
    listaAtualizada = true;
    
    console.log('[AllowedRoulettes] Lista de roletas permitidas atualizada:', roletasPermitidas);
    console.log('[AllowedRoulettes] Nomes de roletas permitidas:', roletasNomePermitidas);
    
    return roletasPermitidas;
  } catch (error) {
    console.error('[AllowedRoulettes] Erro ao buscar roletas disponíveis:', error);
    return ROLETAS_PERMITIDAS_INICIAL;
  }
};

/**
 * Verifica se uma roleta está na lista de roletas permitidas
 * @param rouletteId ID ou nome da roleta a ser verificada
 * @returns boolean indicando se a roleta está permitida
 */
export const isRouletteAllowed = (rouletteId: string): boolean => {
  // Se a lista ainda não foi atualizada, atualize-a
  if (!listaAtualizada) {
    // Iniciar atualização assíncrona
    atualizarRoletasPermitidas().catch(console.error);
    // Enquanto isso, use a lista inicial
    return ROLETAS_PERMITIDAS_INICIAL.includes(rouletteId);
  }
  
  // Verificar se o ID está na lista de IDs permitidos
  if (roletasPermitidas.includes(rouletteId)) {
    return true;
  }
  
  // Verificar se o ID é na verdade um nome e está na lista de nomes permitidos
  if (roletasNomePermitidas.includes(rouletteId)) {
    return true;
  }
  
  return false;
};

/**
 * Filtra um array de roletas para incluir apenas as permitidas
 * @param roulettes Array de roletas
 * @returns Array filtrado contendo apenas roletas permitidas
 */
export const filterAllowedRoulettes = <T extends { id: string; nome?: string }>(roulettes: T[]): T[] => {
  // Se a lista não foi atualizada, tente atualizá-la
  if (!listaAtualizada) {
    atualizarRoletasPermitidas().catch(console.error);
  }
  
  return roulettes.filter(roulette => {
    // Verificar pelo ID
    if (isRouletteAllowed(roulette.id)) {
      return true;
    }
    
    // Verificar pelo nome, se disponível
    if (roulette.nome && isRouletteAllowed(roulette.nome)) {
      return true;
    }
    
    return false;
  });
}; 