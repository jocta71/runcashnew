const express = require('express');
const cors = require('cors');
const { createClient } = require('@supabase/supabase-js');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3002;

// Habilitar CORS para todas as origens
app.use(cors({
  origin: '*', // Permite todas as origens
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'], // Métodos permitidos
  allowedHeaders: ['Content-Type', 'Authorization'] // Headers permitidos
}));

// Middleware
app.use(express.json());

// Supabase client
const supabaseUrl = process.env.SUPABASE_URL || "https://evzqzghxuttctbxgohpx.supabase.co";
const supabaseKey = process.env.SUPABASE_KEY;

const supabase = createClient(supabaseUrl, supabaseKey);

// Endpoint para obter dados das roletas
app.get('/api/roletas', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('roletas')
      .select('*')
      .order('updated_at', { ascending: false });
    
    if (error) {
      console.error('Erro ao buscar roletas:', error);
      return res.status(500).json({ error: 'Erro ao buscar dados das roletas' });
    }
    
    // Garantir que os números mais recentes apareçam primeiro em cada roleta
    const formattedData = data.map(roleta => ({
      ...roleta,
      // Garantir que numeros seja sempre um array, mesmo se for null
      numeros: Array.isArray(roleta.numeros) ? roleta.numeros : [],
      // Calcular win rate
      win_rate: roleta.vitorias + roleta.derrotas > 0 
        ? ((roleta.vitorias / (roleta.vitorias + roleta.derrotas)) * 100).toFixed(1) + '%' 
        : 'N/A'
    }));
    
    return res.json(formattedData);
  } catch (err) {
    console.error('Erro na API:', err);
    return res.status(500).json({ error: 'Erro interno do servidor' });
  }
});

// Endpoint para obter apenas o número mais recente de cada roleta
// Importante: este endpoint deve vir antes do endpoint com parâmetro :id
app.get('/api/roletas/latest', async (req, res) => {
  try {
    const { data, error } = await supabase
      .from('roletas')
      .select('id, nome, numeros, estado_estrategia, numero_gatilho, vitorias, derrotas, sugestao_display, updated_at')
      .order('updated_at', { ascending: false });
    
    if (error) {
      console.error('Erro ao buscar roletas:', error);
      return res.status(500).json({ error: 'Erro ao buscar dados das roletas' });
    }
    
    // Extrair apenas o número mais recente de cada roleta e incluir dados da estratégia
    const latestNumbers = data.map(roleta => ({
      id: roleta.id,
      nome: roleta.nome,
      numero_recente: Array.isArray(roleta.numeros) && roleta.numeros.length > 0 ? roleta.numeros[0] : null,
      estado_estrategia: roleta.estado_estrategia || 'NEUTRAL',
      numero_gatilho: roleta.numero_gatilho || -1,
      vitorias: roleta.vitorias || 0,
      derrotas: roleta.derrotas || 0,
      win_rate: roleta.vitorias + roleta.derrotas > 0 
        ? ((roleta.vitorias / (roleta.vitorias + roleta.derrotas)) * 100).toFixed(1) + '%' 
        : 'N/A',
      sugestao_display: roleta.sugestao_display || '',
      updated_at: roleta.updated_at
    }));
    
    return res.json(latestNumbers);
  } catch (err) {
    console.error('Erro na API:', err);
    return res.status(500).json({ error: 'Erro interno do servidor' });
  }
});

// Endpoint para obter dados de uma roleta específica
app.get('/api/roletas/:id', async (req, res) => {
  try {
    const { id } = req.params;
    const { data, error } = await supabase
      .from('roletas')
      .select('*')
      .eq('id', id)
      .single();
    
    if (error) {
      console.error(`Erro ao buscar roleta ${id}:`, error);
      return res.status(500).json({ error: `Erro ao buscar dados da roleta ${id}` });
    }
    
    // Garantir que numeros seja sempre um array, mesmo se for null
    const formattedData = {
      ...data,
      numeros: Array.isArray(data.numeros) ? data.numeros : [],
      // Calcular win rate
      win_rate: data.vitorias + data.derrotas > 0 
        ? ((data.vitorias / (data.vitorias + data.derrotas)) * 100).toFixed(1) + '%' 
        : 'N/A'
    };
    
    return res.json(formattedData);
  } catch (err) {
    console.error('Erro na API:', err);
    return res.status(500).json({ error: 'Erro interno do servidor' });
  }
});

// Endpoint para health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy' });
});

// Iniciar o servidor
app.listen(PORT, () => {
  console.log(`API rodando na porta ${PORT}`);
});
