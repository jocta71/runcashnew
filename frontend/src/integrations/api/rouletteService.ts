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
