const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');
const { MongoClient } = require('mongodb');
const dotenv = require('dotenv');

// Carregar variáveis de ambiente
dotenv.config();

// Configuração
const PORT = process.env.PORT || 5000;
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/runcash';
const COLLECTION_NAME = 'roleta_numeros';
const POLL_INTERVAL = 2000; // 2 segundos

// Inicializar Express
const app = express();
app.use(cors());
app.use(express.json());

// Criar servidor HTTP
const server = http.createServer(app);

// Inicializar Socket.IO
const io = new Server(server, {
  cors: {
    origin: '*', // Permitir qualquer origem em desenvolvimento
    methods: ['GET', 'POST']
  }
});

// Status e números das roletas
let rouletteStatus = {};
let lastProcessedIds = new Set();

// Conectar ao MongoDB
let db, collection;
let isConnected = false;

async function connectToMongoDB() {
  try {
    const client = new MongoClient(MONGODB_URI, { 
      useNewUrlParser: true, 
      useUnifiedTopology: true 
    });
    
    await client.connect();
    console.log('Conectado ao MongoDB com sucesso');
    
    db = client.db();
    collection = db.collection(COLLECTION_NAME);
    isConnected = true;
    
    // Iniciar o polling para verificar novos dados
    startPolling();
    
    return true;
  } catch (error) {
    console.error('Erro ao conectar ao MongoDB:', error);
    isConnected = false;
    return false;
  }
}

// Função para buscar novos números do MongoDB
async function checkForNewNumbers() {
  if (!isConnected) {
    console.log('Sem conexão com MongoDB, tentando reconectar...');
    await connectToMongoDB();
    return;
  }
  
  try {
    // Obter os últimos 20 números inseridos
    const latestNumbers = await collection
      .find({})
      .sort({ timestamp: -1 })
      .limit(20)
      .toArray();
    
    if (latestNumbers.length === 0) {
      console.log('Nenhum número encontrado na coleção');
      return;
    }
    
    // Processar apenas novos números
    for (const number of latestNumbers) {
      const numberIdStr = number._id.toString();
      
      // Se já processamos este ID, pular
      if (lastProcessedIds.has(numberIdStr)) {
        continue;
      }
      
      // Adicionar ID à lista de processados
      lastProcessedIds.add(numberIdStr);
      
      // Evitar que a lista cresça indefinidamente
      if (lastProcessedIds.size > 100) {
        // Converter para array, remover os mais antigos, e converter de volta para Set
        const idsArray = Array.from(lastProcessedIds);
        lastProcessedIds = new Set(idsArray.slice(-50));
      }
      
      const roletaNome = number.roleta_nome;
      
      // Determinar a cor do número
      let cor = 'verde';
      if (number.numero > 0) {
        const numerosVermelhos = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
        cor = numerosVermelhos.includes(number.numero) ? 'vermelho' : 'preto';
      }
      
      // Formatar o evento
      const event = {
        type: 'new_number',
        roleta_id: number.roleta_id || 'unknown',
        roleta_nome: roletaNome,
        numero: number.numero,
        cor: number.cor || cor,
        timestamp: number.timestamp || new Date().toISOString()
      };
      
      // Emitir evento para todos os clientes subscritos a esta roleta
      io.to(roletaNome).emit('new_number', event);
      
      // Também emitir para o canal global
      io.emit('global_update', event);
      
      console.log(`Emitido número ${number.numero} para roleta ${roletaNome}`);
    }
  } catch (error) {
    console.error('Erro ao verificar novos números:', error);
  }
}

// Iniciar polling para verificar novos dados regularmente
function startPolling() {
  console.log(`Iniciando polling a cada ${POLL_INTERVAL}ms`);
  
  // Verificar imediatamente e depois a cada intervalo
  checkForNewNumbers();
  
  setInterval(checkForNewNumbers, POLL_INTERVAL);
}

// Rota de status da API
app.get('/api/status', (req, res) => {
  res.json({
    status: 'online',
    mongodb_connected: isConnected,
    version: '1.0.0'
  });
});

// Rota para listar todas as roletas
app.get('/api/roulettes', async (req, res) => {
  try {
    if (!isConnected) {
      return res.status(503).json({ error: 'Serviço indisponível: sem conexão com MongoDB' });
    }
    
    // Obter roletas únicas da coleção
    const roulettes = await collection.aggregate([
      { $group: { _id: "$roleta_nome", id: { $first: "$roleta_id" } } },
      { $project: { _id: 0, id: 1, nome: "$_id" } }
    ]).toArray();
    
    res.json(roulettes);
  } catch (error) {
    console.error('Erro ao listar roletas:', error);
    res.status(500).json({ error: 'Erro interno ao buscar roletas' });
  }
});

// Rota para buscar números por nome da roleta
app.get('/api/numbers/:roletaNome', async (req, res) => {
  try {
    if (!isConnected) {
      return res.status(503).json({ error: 'Serviço indisponível: sem conexão com MongoDB' });
    }
    
    const roletaNome = req.params.roletaNome;
    const limit = parseInt(req.query.limit) || 20;
    
    // Buscar números da roleta especificada
    const numbers = await collection
      .find({ roleta_nome: roletaNome })
      .sort({ timestamp: -1 })
      .limit(limit)
      .toArray();
    
    res.json(numbers);
  } catch (error) {
    console.error('Erro ao buscar números da roleta:', error);
    res.status(500).json({ error: 'Erro interno ao buscar números' });
  }
});

// Rota para buscar números por ID da roleta
app.get('/api/numbers/byid/:roletaId', async (req, res) => {
  try {
    if (!isConnected) {
      return res.status(503).json({ error: 'Serviço indisponível: sem conexão com MongoDB' });
    }
    
    const roletaId = req.params.roletaId;
    const limit = parseInt(req.query.limit) || 20;
    
    // Buscar números da roleta especificada
    const numbers = await collection
      .find({ roleta_id: roletaId })
      .sort({ timestamp: -1 })
      .limit(limit)
      .toArray();
    
    res.json(numbers);
  } catch (error) {
    console.error('Erro ao buscar números da roleta:', error);
    res.status(500).json({ error: 'Erro interno ao buscar números' });
  }
});

// Rota para inserir número (para testes)
app.post('/api/numbers', async (req, res) => {
  try {
    if (!isConnected) {
      return res.status(503).json({ error: 'Serviço indisponível: sem conexão com MongoDB' });
    }
    
    const { roleta_nome, roleta_id, numero } = req.body;
    
    if (!roleta_nome || !numero) {
      return res.status(400).json({ error: 'Campos obrigatórios: roleta_nome, numero' });
    }
    
    // Determinar a cor do número
    let cor = 'verde';
    if (numero > 0) {
      const numerosVermelhos = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
      cor = numerosVermelhos.includes(numero) ? 'vermelho' : 'preto';
    }
    
    // Inserir novo número
    const result = await collection.insertOne({
      roleta_nome, 
      roleta_id: roleta_id || 'unknown',
      numero: parseInt(numero),
      cor,
      timestamp: new Date().toISOString()
    });
    
    res.status(201).json({ 
      success: true, 
      message: 'Número inserido com sucesso',
      id: result.insertedId
    });
  } catch (error) {
    console.error('Erro ao inserir número:', error);
    res.status(500).json({ error: 'Erro interno ao inserir número' });
  }
});

// Configuração do Socket.IO
io.on('connection', (socket) => {
  console.log(`Cliente conectado: ${socket.id}`);
  
  // Enviar status de conexão para o cliente
  socket.emit('connection_status', { connected: true, mongodb: isConnected });
  
  // Cliente se inscrevendo para receber atualizações de uma roleta específica
  socket.on('subscribe_to_roleta', (roletaNome) => {
    console.log(`Cliente ${socket.id} se inscreveu para roleta: ${roletaNome}`);
    socket.join(roletaNome);
    
    // Enviar números recentes para o cliente quando ele se inscrever
    if (isConnected) {
      collection
        .find({ roleta_nome: roletaNome })
        .sort({ timestamp: -1 })
        .limit(20)
        .toArray()
        .then(numbers => {
          socket.emit('recent_history', numbers);
        })
        .catch(err => {
          console.error('Erro ao buscar histórico recente:', err);
        });
    }
  });
  
  // Cliente cancelando inscrição
  socket.on('unsubscribe_from_roleta', (roletaNome) => {
    console.log(`Cliente ${socket.id} cancelou inscrição da roleta: ${roletaNome}`);
    socket.leave(roletaNome);
  });
  
  // Desconexão do cliente
  socket.on('disconnect', () => {
    console.log(`Cliente desconectado: ${socket.id}`);
  });
});

// Iniciar o servidor
server.listen(PORT, async () => {
  console.log(`Servidor WebSocket iniciado na porta ${PORT}`);
  
  // Tentar conectar ao MongoDB
  await connectToMongoDB();
});

// Tratar sinais de encerramento do processo
process.on('SIGINT', () => {
  console.log('Encerrando servidor...');
  process.exit(0);
}); 