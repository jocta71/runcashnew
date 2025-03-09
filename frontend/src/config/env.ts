/**
 * Configuração centralizada das variáveis de ambiente
 * 
 * Este arquivo fornece acesso centralizado a todas as variáveis de ambiente
 * utilizadas pelo aplicativo, com valores fallback para desenvolvimento local.
 */

// Interface para tipagem das variáveis de ambiente
interface EnvConfig {
  // URL da API de eventos SSE
  sseServerUrl: string;
  
  // Configurações do Supabase
  supabaseUrl: string;
  supabaseApiKey: string;

  // Indica se estamos em ambiente de produção
  isProduction: boolean;
}

// Verifica se estamos em ambiente de produção
const isProduction = window.location.hostname !== 'localhost' && 
                     window.location.hostname !== '127.0.0.1';

// Função para obter variáveis de ambiente com fallbacks
function getEnvVar(key: string, fallback: string): string {
  // @ts-ignore - Ignorando erro de tipagem do Vite
  const value = import.meta.env[key];
  return value !== undefined ? value : fallback;
}

// Configuração com variáveis de ambiente e valores padrão
const config: EnvConfig = {
  // URL do servidor SSE
  sseServerUrl: getEnvVar(
    'VITE_SSE_SERVER_URL', 
    isProduction 
      ? `${window.location.protocol}//${window.location.host}/events`
      : 'http://localhost:5000/events'
  ),
  
  // Configurações do Supabase
  supabaseUrl: getEnvVar(
    'VITE_SUPABASE_URL',
    'https://evzqzghxuttctbxgohpx.supabase.co'
  ),
  
  supabaseApiKey: getEnvVar(
    'VITE_SUPABASE_API_KEY',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2enF6Z2h4dXR0Y3RieGdvaHB4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3MDY3MjIxMzAsImV4cCI6MjAyMjI5ODEzMH0.Y8ZM1ShjfRPk0VBOPQaLzzxz1Jl0ZvxjZi-z8N0EfOA'
  ),
  
  // Flag de ambiente
  isProduction
};

// Log das configurações carregadas em desenvolvimento
if (!isProduction) {
  console.log('[Config] Variáveis de ambiente carregadas:', {
    sseServerUrl: config.sseServerUrl,
    supabaseUrl: config.supabaseUrl,
    // Não logamos a chave de API completa por segurança
    supabaseApiKey: config.supabaseApiKey.substring(0, 10) + '...',
    isProduction: config.isProduction
  });
}

export default config; 