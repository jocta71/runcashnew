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
const SUPABASE_URL = "https://evzqzghxuttctbxgohpx.supabase.co/rest/v1";
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

export const fetchAllRoulettes = async (): Promise<RouletteData[]> => {
  try {
    console.log('Buscando todas as roletas diretamente do Supabase...');
    
    // Buscar diretamente do Supabase
    const response = await fetch(`${SUPABASE_URL}/roletas?select=*`, {
      headers: {
        'apikey': SUPABASE_KEY,
        'Content-Type': 'application/json',
        'Cache-Control': 'no-cache, no-store'
      }
    });
    
    if (!response.ok) {
      throw new Error(`Erro ao buscar roletas do Supabase: ${response.statusText}`);
    }
    
    const data = await response.json();
    console.log('Roletas encontradas no Supabase:', data.length);
    return data;
  } catch (supabaseError) {
    console.error('Erro ao buscar roletas do Supabase:', supabaseError);
    
    // Fallback para a API apenas se o Supabase falhar
    try {
      console.log('Tentando buscar roletas pela API como fallback...');
      const response = await api.get<RouletteData[]>('/roletas');
      return response.data;
    } catch (apiError) {
      console.error('Erro ao buscar roletas pela API:', apiError);
      throw apiError;
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
    const response = await fetch(`${SUPABASE_URL}/roletas?id=eq.${id}&select=*`, {
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

export const fetchRouletteLatestNumbers = async (roletaId: string, limit = 10): Promise<number[]> => {
  try {
    console.log(`Buscando os ${limit} últimos números da roleta ${roletaId} do Supabase...`);
    
    // Buscar diretamente do Supabase
    const response = await fetch(
      `${SUPABASE_URL}/roleta_numeros?roleta_id=eq.${roletaId}&select=numero,created_at&order=created_at.desc&limit=${limit}`,
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
    console.log(`Encontrados ${data.length} números no Supabase para a roleta ${roletaId}`);
    
    if (Array.isArray(data) && data.length > 0) {
      // Extrair apenas os números (o mais recente primeiro)
      return data.map(item => item.numero);
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
