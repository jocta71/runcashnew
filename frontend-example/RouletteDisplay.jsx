import React, { useState, useEffect } from 'react';
import './RouletteDisplay.css';

// URL da API - Atualize para o endereço do seu backend quando for publicado
const API_URL = 'http://localhost:5000'; // Atualize para sua URL real quando estiver em produção

const RouletteDisplay = () => {
  const [roletas, setRoletas] = useState([]);
  const [numerosRoletas, setNumerosRoletas] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [connected, setConnected] = useState(false);

  // Função para carregar dados iniciais das roletas
  useEffect(() => {
    const fetchRoletas = async () => {
      try {
        setLoading(true);

        // Buscar todas as roletas disponíveis
        const response = await fetch(`${API_URL}/api/roletas`);
        if (!response.ok) {
          throw new Error('Erro ao carregar roletas');
        }

        const data = await response.json();
        setRoletas(data);

        // Para cada roleta, carregar números recentes
        const numerosPromises = data.map(async (roleta) => {
          const numerosResponse = await fetch(`${API_URL}/api/roletas/${roleta.id}/numeros`);
          if (!numerosResponse.ok) {
            throw new Error(`Erro ao carregar números da roleta ${roleta.nome}`);
          }
          const numerosData = await numerosResponse.json();
          return { id: roleta.id, numeros: numerosData.numeros };
        });

        // Aguardar todas as requisições completarem
        const numerosResults = await Promise.all(numerosPromises);
        
        // Organizar números por roleta
        const numerosMap = {};
        numerosResults.forEach(result => {
          numerosMap[result.id] = result.numeros;
        });

        setNumerosRoletas(numerosMap);
        setLoading(false);
      } catch (err) {
        console.error('Erro ao buscar dados:', err);
        setError(err.message);
        setLoading(false);
      }
    };

    fetchRoletas();
  }, []);

  // Conectar ao SSE para atualizações em tempo real
  useEffect(() => {
    let eventSource = null;

    const connectSSE = () => {
      eventSource = new EventSource(`${API_URL}/api/events`);

      eventSource.onopen = () => {
        console.log('Conexão SSE estabelecida');
        setConnected(true);
      };

      eventSource.onmessage = (event) => {
        try {
          const eventData = JSON.parse(event.data);
          console.log('Evento recebido:', eventData);

          // Tratar eventos de novos números
          if (eventData.type === 'new_number') {
            setNumerosRoletas(prev => {
              const roletaId = eventData.roleta_id;
              
              // Se a roleta não existe nos dados atuais, ignorar
              if (!prev[roletaId]) return prev;
              
              // Adicionar novo número no início da lista
              const numerosAtualizados = [
                { 
                  numero: eventData.numero, 
                  cor: eventData.cor || determinarCor(eventData.numero),
                  timestamp: eventData.timestamp 
                },
                ...prev[roletaId].slice(0, 49) // Manter até 50 números
              ];
              
              return {
                ...prev,
                [roletaId]: numerosAtualizados
              };
            });
          }
        } catch (err) {
          console.error('Erro ao processar evento:', err);
        }
      };

      eventSource.onerror = (error) => {
        console.error('Erro na conexão SSE:', error);
        setConnected(false);
        
        // Tentar reconectar após 5 segundos em caso de erro
        eventSource.close();
        setTimeout(connectSSE, 5000);
      };
    };

    // Iniciar conexão SSE
    connectSSE();

    // Limpar ao desmontar o componente
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, []);

  // Função auxiliar para determinar a cor de um número
  const determinarCor = (numero) => {
    numero = parseInt(numero);
    if (numero === 0) return 'verde';
    
    const vermelhos = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
    return vermelhos.includes(numero) ? 'vermelho' : 'preto';
  };

  // Renderizar mensagem de carregamento
  if (loading) {
    return <div className="loading">Carregando dados das roletas...</div>;
  }

  // Renderizar mensagem de erro
  if (error) {
    return <div className="error">Erro: {error}</div>;
  }

  return (
    <div className="roletas-container">
      <div className="connection-status">
        Status da conexão: {connected ? '🟢 Conectado' : '🔴 Desconectado'}
      </div>

      {roletas.map(roleta => (
        <div key={roleta.id} className="roleta-card">
          <h2 className="roleta-title">{roleta.nome}</h2>
          
          <div className="numeros-container">
            {numerosRoletas[roleta.id]?.map((num, index) => (
              <div 
                key={`${roleta.id}-${index}-${num.numero}`} 
                className={`numero-ball ${num.cor || determinarCor(num.numero)}`}
              >
                {num.numero}
              </div>
            ))}
            
            {(!numerosRoletas[roleta.id] || numerosRoletas[roleta.id].length === 0) && (
              <div className="no-data">Sem números disponíveis</div>
            )}
          </div>
        </div>
      ))}
    </div>
  );
};

export default RouletteDisplay; 