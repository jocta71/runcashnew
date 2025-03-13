const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const { MongoClient } = require('mongodb');
const cors = require('cors');
const dotenv = require('dotenv');

// Carregar variáveis de ambiente
dotenv.config();

// Configuração Express
const app = express();
app.use(cors());
app.use(express.json());

// Configuração do servidor HTTP
const server = http.createServer(app);

// Configuração do Socket.IO
const io = new Server(server, {
  cors: {
    origin: process.env.ALLOWED_ORIGINS ? process.env.ALLOWED_ORIGINS.split(',') : ['https://runcashnew-frontend-nu.vercel.app', 'http://localhost:3000'],
    methods: ["GET", "POST"]
  }
});

// Conexão com MongoDB
const MONGODB_URI = process.env.MONGODB_URI || 'mongodb://localhost:27017/runcash';
const MONGODB_DB_NAME = process.env.MONGODB_DB_NAME || 'runcash';
let db, roletaNumerosCollection;

// Variáveis para controle de polling
let lastCheckedId = null;
let pollingInterval = null;
const POLLING_INTERVAL_MS = 1000; // 1 segundo

// Status endpoint para verificação de saúde
app.get('/api/status', (req, res) => {
  res.json({
    status: 'online',
    version: '1.0.0',
    service: 'WebSocket Server',
    timestamp: new Date().toISOString()
  });
});

// Rota para obter todas as roletas
app.get('/api/roletas', async (req, res) => {
  try {
    const roletasCollection = db.collection('roletas');
    const roletas = await roletasCollection.find({ ativa: true }).toArray();
    
    // Converter _id para id para manter compatibilidade com frontend existente
    const formattedRoletas = roletas.map(roleta => ({
      id: roleta._id,
      nome: roleta.nome,
      ...roleta
    }));
    
    res.json(formattedRoletas);
  } catch (error) {
    console.error('Erro ao obter roletas:', error);
    res.status(500).json({ error: 'Erro ao obter roletas' });
  }
});

// Rota para obter números de uma roleta específica
app.get('/api/roletas/:id/numeros', async (req, res) => {
  try {
    const roletaId = req.params.id;
    const numeros = await roletaNumerosCollection
      .find({ roleta_id: roletaId })
      .sort({ timestamp: -1 })
      .limit(50)
      .toArray();
    
    res.json({ numeros });
  } catch (error) {
    console.error('Erro ao obter números da roleta:', error);
    res.status(500).json({ error: 'Erro ao obter números da roleta' });
  }
});

// Iniciar servidor e configurar Socket.IO
async function startServer() {
  try {
    // Conectar ao MongoDB
    const client = new MongoClient(MONGODB_URI);
    await client.connect();
    console.log('Conectado ao MongoDB');
    
    db = client.db(MONGODB_DB_NAME);
    roletaNumerosCollection = db.collection('roleta_numeros');
    
    // Iniciar polling controlado para detecção de mudanças
    startPolling();
    
    // Socket.IO connection handling
    io.on('connection', (socket) => {
      console.log('Nova conexão estabelecida:', socket.id);
      
      // Enviar histórico recente ao conectar
      sendRecentHistory(socket);
      
      socket.on('disconnect', () => {
        console.log('Cliente desconectado:', socket.id);
      });
      
      // Subscrição para roleta específica
      socket.on('subscribe_to_roleta', (roletaId) => {
        console.log(`Cliente ${socket.id} se inscreveu na roleta: ${roletaId}`);
        socket.join(`roleta:${roletaId}`);
      });
    });
    
    // Iniciar servidor HTTP
    const PORT = process.env.PORT || 5001;
    server.listen(PORT, () => {
      console.log(`Servidor Socket.IO rodando na porta ${PORT}`);
      console.log(`API disponível em http://localhost:${PORT}/api/status`);
    });
  } catch (error) {
    console.error('Erro ao iniciar servidor:', error);
  }
}

// Iniciar polling controlado para buscar novos itens
function startPolling() {
  console.log('Iniciando polling controlado para substituir Change Streams');
  
  // Buscar o último documento inserido para comparação futura
  getLastDocument().then(lastDoc => {
    if (lastDoc) {
      lastCheckedId = lastDoc._id;
      console.log(`Último documento encontrado: ${lastDoc._id}`);
    }
    
    // Iniciar polling em intervalos definidos
    pollingInterval = setInterval(checkForNewDocuments, POLLING_INTERVAL_MS);
  });
  
  // Adicionar limpeza ao encerrar o processo
  process.on('SIGINT', () => {
    if (pollingInterval) {
      clearInterval(pollingInterval);
    }
    console.log('Polling interrompido, encerrando aplicação');
    process.exit(0);
  });
}

// Obter o documento mais recente da coleção
async function getLastDocument() {
  try {
    return await roletaNumerosCollection
      .find({})
      .sort({ _id: -1 })
      .limit(1)
      .next();
  } catch (error) {
    console.error('Erro ao obter último documento:', error);
    return null;
  }
}

// Verificar novos documentos periodicamente
async function checkForNewDocuments() {
  try {
    let query = {};
    if (lastCheckedId) {
      query = { _id: { $gt: lastCheckedId } };
    }
    
    const newDocuments = await roletaNumerosCollection
      .find(query)
      .sort({ _id: 1 })
      .toArray();
    
    if (newDocuments.length > 0) {
      console.log(`Encontrados ${newDocuments.length} novos documentos`);
      
      // Atualizar o último ID verificado
      lastCheckedId = newDocuments[newDocuments.length - 1]._id;
      
      // Processar cada novo documento
      for (const doc of newDocuments) {
        processNewDocument(doc);
      }
    }
  } catch (error) {
    console.error('Erro ao verificar novos documentos:', error);
  }
}

// Processar novo documento encontrado
function processNewDocument(doc) {
  const eventData = {
    type: 'new_number',
    roleta_id: doc.roleta_id,
    roleta_nome: doc.roleta_nome,
    numero: doc.numero,
    cor: doc.cor,
    timestamp: doc.timestamp
  };
  
  console.log(`Novo número detectado e enviado por Socket.IO: ${doc.roleta_nome} - ${doc.numero}`);
  
  // Emitir evento para todos os clientes
  io.emit('new_number', eventData);
  
  // Emitir também para a sala da roleta específica
  io.to(`roleta:${doc.roleta_id}`).emit('new_number', eventData);
}

// Enviar histórico recente ao cliente
async function sendRecentHistory(socket) {
  try {
    // Buscar números recentes para enviar ao cliente que acabou de conectar
    const recentNumbers = await roletaNumerosCollection
      .find({})
      .sort({ timestamp: -1 })
      .limit(50)
      .toArray();
    
    if (recentNumbers.length > 0) {
      console.log(`Enviando histórico recente (${recentNumbers.length} números) para cliente ${socket.id}`);
      socket.emit('recent_history', recentNumbers);
    }
  } catch (error) {
    console.error('Erro ao enviar histórico recente:', error);
  }
}

// Iniciar o servidor
startServer().catch(console.error);

// Tratamento de encerramento gracioso
process.on('SIGINT', async () => {
  if (pollingInterval) {
    clearInterval(pollingInterval);
  }
  console.log('Encerrando servidor WebSocket...');
  process.exit(0);
}); 