import axios from 'axios';

const API_URL = 'http://localhost:3001/api';

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
    const response = await axios.get<RouletteData[]>(`${API_URL}/roletas`);
    return response.data;
  } catch (error) {
    console.error('Erro ao buscar roletas:', error);
    throw error;
  }
};

export const fetchLatestRouletteNumbers = async (): Promise<LatestRouletteNumber[]> => {
  try {
    const response = await axios.get<LatestRouletteNumber[]>(`${API_URL}/roletas/latest`);
    return response.data;
  } catch (error) {
    console.error('Erro ao buscar números mais recentes das roletas:', error);
    throw error;
  }
};

export const fetchRouletteById = async (id: string): Promise<RouletteData> => {
  try {
    const response = await axios.get<RouletteData>(`${API_URL}/roletas/${id}`);
    return response.data;
  } catch (error) {
    console.error(`Erro ao buscar roleta ${id}:`, error);
    throw error;
  }
};
