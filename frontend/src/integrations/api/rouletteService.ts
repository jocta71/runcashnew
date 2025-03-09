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
    const response = await api.get<RouletteData[]>('/roletas');
    return response.data;
  } catch (error) {
    console.error('Erro ao buscar roletas:', error);
    throw error;
  }
};

export const fetchLatestRouletteNumbers = async (): Promise<LatestRouletteNumber[]> => {
  try {
    const response = await api.get<LatestRouletteNumber[]>('/roletas/latest');
    return response.data;
  } catch (error) {
    console.error('Erro ao buscar números mais recentes das roletas:', error);
    throw error;
  }
};

export const fetchRouletteById = async (id: string): Promise<RouletteData> => {
  try {
    const response = await api.get<RouletteData>(`/roletas/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao buscar roleta ${id}:`, error);
    throw error;
  }
};

export const fetchRouletteLatestNumbers = async (roletaId: string, limit = 10): Promise<number[]> => {
  try {
    // Primeiro tentamos a API
    try {
      const response = await api.get<RouletteNumberRecord[]>(`/roleta_numeros/${roletaId}?limit=${limit}`);
      if (response.data && Array.isArray(response.data)) {
        return response.data.map(record => record.numero);
      }
    } catch (apiError) {
      console.warn('Erro ao buscar números via API, tentando Supabase diretamente:', apiError);
    }
    
    // Fallback: buscar diretamente do Supabase se a API falhar
    const supabaseUrl = "https://evzqzghxuttctbxgohpx.supabase.co/rest/v1/roleta_numeros";
    const supabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDExNzc5OTEsImV4cCI6MjA1Njc1Mzk5MX0.CmoM_y0i36nbBx2iN0DlOIob3yAgVRM1xY_XiOFBZLQ";
    
    const response = await fetch(
      `${supabaseUrl}?roleta_id=eq.${roletaId}&select=numero,created_at&order=created_at.desc&limit=${limit}`,
      {
        headers: {
          'apikey': supabaseKey,
          'Content-Type': 'application/json',
          'Cache-Control': 'no-cache, no-store'
        }
      }
    );
    
    if (!response.ok) {
      throw new Error(`Erro ao buscar números da roleta: ${response.statusText}`);
    }
    
    const data = await response.json();
    if (Array.isArray(data) && data.length > 0) {
      // Extrair apenas os números e inverter para ter o mais recente primeiro
      return data.map(item => item.numero).reverse();
    }
    
    return [];
  } catch (error) {
    console.error(`Erro ao buscar últimos números para roleta ${roletaId}:`, error);
    return [];
  }
};
