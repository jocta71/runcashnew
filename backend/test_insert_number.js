const axios = require('axios');

// Configurações
const API_URL = 'http://localhost:5000/api/numbers';

// Função para gerar um número aleatório da roleta (0-36)
function getRandomNumber() {
  return Math.floor(Math.random() * 37);
}

// Função para inserir um número na API
async function insertNumber(roletaNome, numero) {
  try {
    console.log(`Inserindo número ${numero} na roleta ${roletaNome}...`);
    
    const response = await axios.post(API_URL, {
      roleta_nome: roletaNome,
      roleta_id: getRouletteId(roletaNome),
      numero: numero
    });
    
    console.log('Resposta:', response.data);
    console.log('Número inserido com sucesso!');
    return true;
  } catch (error) {
    console.error('Erro ao inserir número:', error.message);
    if (error.response) {
      console.error('Detalhes:', error.response.data);
    }
    return false;
  }
}

// Mapear nomes de roletas para IDs fixos
function getRouletteId(roletaNome) {
  const rouletteIds = {
    'Lightning Roulette': '23d683ae-7b17-89e3-eccb-30a3083338f0',
    'Auto-Roulette': '48f8b26b-4dfa-5c87-a372-6f69e2902c57',
    'Speed Auto Roulette': '1a3ae55f-534e-5d99-8ef8-16d20466fc36',
    'Immersive Roulette': '72a4217f-a3c4-5f81-a0ad-41c307110c99',
    'Roulette Live': '3a90c765-f34d-547f-81c0-f99b9f11a61f',
    'Brazilian Mega Roulette': 'b5c26323-67ab-5576-aa17-88da4ced1a86'
  };
  
  return rouletteIds[roletaNome] || 'unknown-id';
}

// Executar o script com os argumentos da linha de comando
async function main() {
  // Obter argumentos da linha de comando
  const args = process.argv.slice(2);
  
  // Valores padrão
  let roletaNome = 'Lightning Roulette';
  let numero = getRandomNumber();
  
  // Processar argumentos
  if (args.length >= 1) {
    roletaNome = args[0];
  }
  
  if (args.length >= 2) {
    numero = parseInt(args[1]);
    
    // Validar se o número está no intervalo permitido
    if (isNaN(numero) || numero < 0 || numero > 36) {
      console.error('Erro: O número deve estar entre 0 e 36');
      process.exit(1);
    }
  }
  
  // Inserir o número
  const success = await insertNumber(roletaNome, numero);
  
  // Sair com código de status apropriado
  process.exit(success ? 0 : 1);
}

// Executar o script
main(); 