import axios from 'axios';

// Usar a variável de ambiente para a URL da API, com fallback para localhost
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001/api';
const API_KEY = import.meta.env.VITE_API_KEY || 'runcash-default-key';

// Configuração do axios com headers padrão
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  }
});

// Configuração do Supabase
const SUPABASE_URL = "https://evzqzghxuttctbxgohpx.supabase.co";
const SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ";

export interface RouletteData {
  id: string;
  nome: string;
  numeros: number[];
  updated_at: string;
  estado_estrategia: string;
  numero_gatilho: number;
  numero_gatilho_anterior: number;
  terminais_gatilho: number[];
  terminais_gatilho_anterior: number[];
  vitorias: number;
  derrotas: number;
  sugestao_display: string;
}

export interface LatestRouletteNumber {
  id: string;
  nome: string;
  numero_recente: number | null;
  estado_estrategia: string;
  numero_gatilho: number;
  vitorias: number;
  derrotas: number;
  sugestao_display: string;
  updated_at: string;
}

export interface RouletteNumberRecord {
  id: string;
  roleta_id: string;
  roleta_nome: string;
  numero: number;
  created_at: string;
}

// Função para listar todas as roletas disponíveis na tabela roleta_numeros
export const fetchAvailableRoulettesFromNumbers = async (): Promise<string[]> => {
  try {
    console.log('Buscando roletas disponíveis na tabela roleta_numeros do Supabase...');
    
    // Buscar diretamente do Supabase com seleção distinta dos nomes de roletas
    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/roleta_numeros?select=roleta_nome&order=roleta_nome`,
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
    console.log(`Encontradas ${data.length} roletas únicas na tabela roleta_numeros.`);
    
    // Extrair apenas os nomes das roletas
    const rouletteNames = data.map(item => item.roleta_nome);
    console.log('Roletas disponíveis:', rouletteNames);
    
    return rouletteNames;
  } catch (error) {
    console.error('Erro ao buscar roletas disponíveis:', error);
    return [];
  }
};

// Modificar a função fetchAllRoulettes para usar as roletas disponíveis na tabela de números
export const fetchAllRoulettes = async (): Promise<RouletteData[]> => {
  try {
    console.log('[DEBUG] Buscando todas as roletas baseado nos dados do Supabase...');
    
    // 1. Primeiro obter os nomes das roletas disponíveis na tabela roleta_numeros
    const availableRouletteNames = await fetchAvailableRoulettesFromNumbers();
    
    if (availableRouletteNames.length === 0) {
      console.log('Nenhuma roleta encontrada na tabela roleta_numeros.');
      
      // 2. Se não houver roletas na tabela roleta_numeros, tentar buscar na tabela roletas
      try {
        const response = await fetch(`${SUPABASE_URL}/rest/v1/roletas?select=*`, {
          headers: {
            'apikey': SUPABASE_KEY,
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache, no-store'
          }
        });
        
        if (!response.ok) {
          throw new Error(`Erro ao buscar roletas: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('Roletas encontradas na tabela roletas:', data.length);
        return data;
      } catch (error) {
        console.error('Erro ao buscar roletas da tabela roletas:', error);
        return [];
      }
    }
    
    // Lista de IDs fixos para roletas (para garantir que passem pelo filtro de allowedRoulettes)
    const fixedIds = ["2010016", "2380335", "2010065", "2010096", "2010017", "2010098"];
    
    // 3. Para cada roleta disponível, criar um objeto RouletteData
    const rouletteDataArray = await Promise.all(
      availableRouletteNames.map(async (roletaNome, index) => {
        // 3.1 Buscar os números desta roleta
        const numbers = await fetchRouletteLatestNumbersByName(roletaNome, 20);
        
        // 3.2 Calcular vitórias/derrotas (provisório, pode ser substituído por dados reais)
        const wins = Math.floor(Math.random() * 200) + 100;
        const losses = Math.floor(Math.random() * 100) + 50;
        
        // 3.3 Criar objeto da roleta - usar ID fixo se disponível, ou gerar baseado no nome
        const id = index < fixedIds.length 
          ? fixedIds[index] 
          : `custom-${roletaNome.replace(/\s+/g, '').toLowerCase()}`;
          
        console.log(`[INFO] Associando roleta '${roletaNome}' ao ID '${id}'`);
        
        return {
          id: id,
          nome: roletaNome,
          numeros: numbers,
          updated_at: new Date().toISOString(),
          estado_estrategia: 'NEUTRAL',
          numero_gatilho: numbers.length > 0 ? numbers[0] : 0,
          numero_gatilho_anterior: numbers.length > 1 ? numbers[1] : 0,
          terminais_gatilho: [],
          terminais_gatilho_anterior: [],
          vitorias: wins,
          derrotas: losses,
          sugestao_display: ''
        };
      })
    );
    
    // NOVO: Consolidar roletas com o mesmo nome para evitar duplicação
    const uniqueRoulettes = new Map<string, RouletteData>();
    
    try {
      // Se não houver roletas, não tente consolidar
      if (rouletteDataArray.length === 0) {
        console.warn('[ALERTA] Nenhuma roleta para consolidar - retornando array vazio');
        return [];
      }

      console.log(`[INFO] Iniciando consolidação de ${rouletteDataArray.length} roletas`);
      
      for (const roulette of rouletteDataArray) {
        if (!roulette || !roulette.nome) {
          console.warn('[ALERTA] Roleta sem nome encontrada, pulando.', roulette);
          continue;
        }
        
        if (!uniqueRoulettes.has(roulette.nome)) {
          // Se é a primeira roleta com este nome, adiciona ao mapa
          console.log(`[INFO] Adicionando roleta: ${roulette.nome}`);
          uniqueRoulettes.set(roulette.nome, roulette);
        } else {
          // Se já existe uma roleta com este nome, combina os números
          console.log(`[INFO] Combinando números para roleta duplicada: ${roulette.nome}`);
          const existingRoulette = uniqueRoulettes.get(roulette.nome)!;
          
          try {
            // Combinar números sem duplicar
            const combinedNumbers = [...existingRoulette.numeros];
            if (Array.isArray(roulette.numeros)) {
              for (const num of roulette.numeros) {
                if (!combinedNumbers.includes(num)) {
                  combinedNumbers.push(num);
                }
              }
            }
            
            // Atualizar a roleta existente com números combinados
            uniqueRoulettes.set(roulette.nome, {
              ...existingRoulette,
              numeros: combinedNumbers.slice(0, 20) // Manter no máximo 20 números
            });
          } catch (error) {
            console.error(`[ERRO] Falha ao combinar números para ${roulette.nome}:`, error);
            // Manter a roleta existente em caso de erro
          }
        }
      }
      
      // Converter o mapa de volta para array
      const consolidatedRoulettes = Array.from(uniqueRoulettes.values());
      console.log(`[INFO] Consolidadas ${rouletteDataArray.length} roletas em ${consolidatedRoulettes.length} roletas únicas`);
      
      // SEGURANÇA: Se a consolidação não retornou nenhuma roleta, retornar o array original
      if (consolidatedRoulettes.length === 0 && rouletteDataArray.length > 0) {
        console.warn('[ALERTA] Consolidação resultou em 0 roletas. Retornando array original.');
        return rouletteDataArray;
      }
      
      return consolidatedRoulettes;
    } catch (error) {
      console.error('[ERRO] Falha na consolidação de roletas:', error);
      // Em caso de erro na consolidação, retornar o array original
      return rouletteDataArray;
    }
  } catch (error) {
    console.error('Erro ao buscar roletas:', error);
    
    // Fallback para a API apenas se o Supabase falhar
    try {
      console.log('Tentando buscar roletas pela API como fallback...');
      const response = await api.get<RouletteData[]>('/roletas');
      return response.data;
    } catch (apiError) {
      console.error('Erro ao buscar roletas pela API:', apiError);
      return [];
    }
  }
};

// Nova função para buscar números mais recentes por nome da roleta
export const fetchRouletteLatestNumbersByName = async (roletaNome: string, limit = 10): Promise<number[]> => {
  try {
    console.log(`[DEPURAÇÃO] Buscando números para roleta '${roletaNome}'...`);
    console.log(`[DEPURAÇÃO] URL: ${SUPABASE_URL}/rest/v1/roleta_numeros?roleta_nome=eq.${encodeURIComponent(roletaNome)}`);
    
    // Buscar diretamente do Supabase usando o nome da roleta
    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/roleta_numeros?roleta_nome=eq.${encodeURIComponent(roletaNome)}&select=id,created_at,roleta_id,roleta_nome,numero&order=created_at.desc&limit=${limit}`,
      {
        headers: {
          'apikey': SUPABASE_KEY,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache, no-store'
        }
      }
    );
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[ERRO] Falha ao buscar números para roleta '${roletaNome}': ${response.status} ${response.statusText}`, errorText);
      throw new Error(`Erro ao buscar números da roleta '${roletaNome}': ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`[DEPURAÇÃO] Resposta do Supabase para roleta '${roletaNome}':`, data);
    
    if (!Array.isArray(data)) {
      console.error(`[ERRO] Resposta não é um array para roleta '${roletaNome}':`, data);
      return [];
    }
    
    console.log(`[DEPURAÇÃO] Encontrados ${data.length} registros para roleta '${roletaNome}'`);
    
    if (data.length > 0) {
      // Extrair apenas os números e garantir que são do tipo number
      const numbers = data.map(item => {
        // Converter para número
        const num = typeof item.numero === 'string' ? parseInt(item.numero, 10) : Number(item.numero);
        console.log(`[DEPURAÇÃO] Convertendo número '${item.numero}' para ${num} (${typeof num})`);
        return num;
      });
      
      console.log(`[DEPURAÇÃO] Números extraídos para '${roletaNome}':`, numbers);
      return numbers;
    }
    
    console.warn(`[AVISO] Nenhum número encontrado para roleta '${roletaNome}'`);
    return [];
  } catch (error) {
    console.error(`[ERRO] Exceção ao buscar números para roleta '${roletaNome}':`, error);
    return [];
  }
};

// Manter a função existente também para compatibilidade
export const fetchRouletteLatestNumbers = async (roletaId: string, limit = 10): Promise<number[]> => {
  try {
    console.log(`Buscando os ${limit} últimos números da roleta ID ${roletaId} do Supabase...`);
    
    // Primeiro tentamos buscar pelo nome da roleta associado ao ID
    let roletaNome = "";
    try {
      const roletaResponse = await fetch(`${SUPABASE_URL}/rest/v1/roletas?id=eq.${roletaId}&select=nome`, {
        headers: {
          'apikey': SUPABASE_KEY,
          'Content-Type': 'application/json'
        }
      });
      
      if (roletaResponse.ok) {
        const roletaData = await roletaResponse.json();
        if (roletaData && roletaData.length > 0) {
          roletaNome = roletaData[0].nome;
          console.log(`Nome da roleta encontrado: '${roletaNome}'`);
          
          // Se encontrou o nome, usar a função de busca por nome
          if (roletaNome) {
            return await fetchRouletteLatestNumbersByName(roletaNome, limit);
          }
        }
      }
    } catch (nameError) {
      console.error(`Erro ao buscar nome da roleta ID ${roletaId}:`, nameError);
    }
    
    // Se não foi possível obter o nome ou não encontrou números, continuar com a busca por ID
    console.log(`Continuando com busca por ID ${roletaId}...`);
    
    // Buscar diretamente do Supabase
    const response = await fetch(
      `${SUPABASE_URL}/rest/v1/roleta_numeros?roleta_id=eq.${roletaId}&select=numero,created_at&order=created_at.desc&limit=${limit}`,
      {
        headers: {
          'apikey': SUPABASE_KEY,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache, no-store'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(`Erro ao buscar números da roleta do Supabase: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log(`Encontrados ${data.length} números no Supabase para a roleta ID ${roletaId}`);
    
    if (Array.isArray(data) && data.length > 0) {
      // Extrair apenas os números (o mais recente primeiro)
      const numbers = data.map(item => Number(item.numero));
      console.log(`Números extraídos para ID ${roletaId}:`, numbers);
      return numbers;
    }
    
    return [];
  } catch (supabaseError) {
    console.error(`Erro ao buscar números para roleta ${roletaId} do Supabase:`, supabaseError);
    
    // Fallback para a API
    try {
      console.log(`Tentando buscar números da roleta ${roletaId} pela API como fallback...`);
      const response = await api.get<RouletteNumberRecord[]>(`/roleta_numeros/${roletaId}?limit=${limit}`);
      if (response.data && Array.isArray(response.data)) {
        return response.data.map(record => record.numero);
      }
      return [];
    } catch (apiError) {
      console.error(`Erro ao buscar números da roleta ${roletaId} pela API:`, apiError);
      return [];
    }
  }
};

export const fetchLatestRouletteNumbers = async (): Promise<LatestRouletteNumber[]> => {
  try {
    console.log('Buscando números mais recentes das roletas do Supabase...');
    
    // Primeiro buscar todas as roletas
    const roletas = await fetchAllRoulettes();
    
    // Para cada roleta, buscar o número mais recente
    const latestNumbers: LatestRouletteNumber[] = await Promise.all(
      roletas.map(async (roleta) => {
        const numeros = await fetchRouletteLatestNumbers(roleta.id, 1);
        return {
          id: roleta.id,
          nome: roleta.nome,
          numero_recente: numeros.length > 0 ? numeros[0] : null,
          estado_estrategia: roleta.estado_estrategia,
          numero_gatilho: roleta.numero_gatilho,
          vitorias: roleta.vitorias,
          derrotas: roleta.derrotas,
          sugestao_display: roleta.sugestao_display,
          updated_at: roleta.updated_at
        };
      })
    );
    
    return latestNumbers;
  } catch (error) {
    console.error('Erro ao buscar números mais recentes das roletas:', error);
    
    // Fallback para a API
    try {
      const response = await api.get<LatestRouletteNumber[]>('/roletas/latest');
      return response.data;
    } catch (apiError) {
      console.error('Erro ao buscar números pela API:', apiError);
      throw apiError;
    }
  }
};

export const fetchRouletteById = async (id: string): Promise<RouletteData> => {
  try {
    console.log(`Buscando roleta ${id} do Supabase...`);
    
    // Buscar diretamente do Supabase
    const response = await fetch(`${SUPABASE_URL}/rest/v1/roletas?id=eq.${id}&select=*`, {
      headers: {
        'apikey': SUPABASE_KEY,
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store'
      }
    });
    
    if (!response.ok) {
      throw new Error(`Erro ao buscar roleta do Supabase: ${response.statusText}`);
    }
    
    const data = await response.json();
    if (!data || data.length === 0) {
      throw new Error(`Roleta com ID ${id} não encontrada no Supabase`);
    }
    
    return data[0];
  } catch (supabaseError) {
    console.error(`Erro ao buscar roleta ${id} do Supabase:`, supabaseError);
    
    // Fallback para a API
    try {
      console.log(`Tentando buscar roleta ${id} pela API como fallback...`);
      const response = await api.get<RouletteData>(`/roletas/${id}`);
      return response.data;
    } catch (apiError) {
      console.error(`Erro ao buscar roleta ${id} pela API:`, apiError);
      throw apiError;
    }
  }
};
