/**
 * Script para inserir um conjunto de dados de exemplo no MongoDB
 * Isso permite testar o sistema facilmente sem precisar inserir números manualmente
 */
const axios = require('axios');

// Configurações
const API_URL = 'http://localhost:5000/api/numbers';

// Dados de roletas disponíveis
const roletas = [
  { nome: 'Lightning Roulette', id: '23d683ae-7b17-89e3-eccb-30a3083338f0' },
  { nome: 'Auto-Roulette', id: '48f8b26b-4dfa-5c87-a372-6f69e2902c57' },
  { nome: 'Speed Auto Roulette', id: '1a3ae55f-534e-5d99-8ef8-16d20466fc36' },
  { nome: 'Immersive Roulette', id: '72a4217f-a3c4-5f81-a0ad-41c307110c99' },
  { nome: 'Roulette Live', id: '3a90c765-f34d-547f-81c0-f99b9f11a61f' },
  { nome: 'Brazilian Mega Roulette', id: 'b5c26323-67ab-5576-aa17-88da4ced1a86' }
];

// Função para gerar um número aleatório da roleta (0-36)
function getRandomNumber() {
  return Math.floor(Math.random() * 37);
}

// Função para inserir um número na API
async function insertNumber(roletaNome, roletaId, numero) {
  try {    
    const response = await axios.post(API_URL, {
      roleta_nome: roletaNome,
      roleta_id: roletaId,
      numero: numero
    });
    
    return response.data;
  } catch (error) {
    console.error(`Erro ao inserir número ${numero} para roleta ${roletaNome}:`, error.message);
    if (error.response) {
      console.error('Detalhes:', error.response.data);
    }
    return null;
  }
}

// Função para esperar um determinado tempo em milissegundos
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Função para inserir um conjunto de números para uma roleta
async function insertBatchForRoulette(roleta, quantity, delayBetweenInserts = 100) {
  console.log(`Inserindo ${quantity} números para a roleta ${roleta.nome}...`);
  
  const results = [];
  for (let i = 0; i < quantity; i++) {
    const numero = getRandomNumber();
    const result = await insertNumber(roleta.nome, roleta.id, numero);
    
    if (result) {
      console.log(`[${i+1}/${quantity}] Inserido número ${numero} para ${roleta.nome}`);
      results.push(result);
      // Pequeno atraso para evitar sobrecarga na API
      await sleep(delayBetweenInserts);
    } else {
      console.error(`Falha ao inserir número ${numero} para ${roleta.nome}`);
    }
  }
  
  return results;
}

// Função principal para inserir dados de exemplo
async function insertSampleData() {
  console.log("Iniciando inserção de dados de exemplo...");
  console.log(`Processando ${roletas.length} roletas`);
  
  // Processar cada roleta, inserindo 10 números para cada uma
  for (const roleta of roletas) {
    await insertBatchForRoulette(roleta, 10);
    // Aguardar um pouco entre roletas
    await sleep(500);
  }
  
  console.log("Inserção de dados de exemplo concluída!");
}

// Executar a função principal
insertSampleData()
  .then(() => {
    console.log("Script finalizado com sucesso");
    process.exit(0);
  })
  .catch(error => {
    console.error("Erro ao executar script:", error);
    process.exit(1);
  }); 