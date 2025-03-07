import React, { useState, useEffect, useRef } from 'react';
import ChatHeader from './chat/ChatHeader';
import ChatMessageList from './chat/ChatMessageList';
import ChatInput from './chat/ChatInput';
import ChatSettings from './chat/ChatSettings';
import { ChatMessage } from './chat/types';
import { generateAIResponse, simulateChat, stopChatSimulation } from '@/integrations/ai/chatService';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

const ChatUI = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      sender: 'Zé das Couves',
      message: 'Quando que vai ficar pronto, mano?',
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 60 * 5)
    },
    {
      id: 2,
      sender: 'Fernandinha',
      message: 'Tô mó ansiedade pra jogar, viu?',
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 60 * 4)
    },
    {
      id: 3,
      sender: 'Moderador',
      message: 'Galera, calma que já vai rolar!',
      isModerator: true,
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 60 * 3)
    },
    {
      id: 4,
      sender: 'Bia',
      message: 'Tô nem aí, só quero ganhar uma grana!',
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 60 * 2)
    },
    {
      id: 5,
      sender: 'Juninho',
      message: 'Recebeu minha mensagem?',
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 60 * 1)
    },
    {
      id: 6,
      sender: 'Admin',
      message: 'Cês falaram com o entregador? Mó vacilo, tá atrasado mais de uma hora!',
      isAdmin: true,
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 30)
    },
    {
      id: 7,
      sender: 'Robertão',
      message: 'Mano, esse app é show de bola!',
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 20)
    },
    {
      id: 8,
      sender: 'Paty',
      message: 'Tá top demais, curti mesmo!',
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 15)
    },
    {
      id: 9,
      sender: 'Dudinha',
      message: 'Blz',
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 10)
    },
    {
      id: 10,
      sender: 'Matheuzinho',
      message: 'Fala aí, quando vai rolar a nova roleta?',
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date(Date.now() - 1000 * 5)
    },
    {
      id: 11,
      sender: 'Você',
      message: 'Fala galera! Qual a boa?',
      avatar: '/lovable-uploads/433b5fd4-2378-47fe-9d10-276fead4ebce.png',
      timestamp: new Date()
    }
  ]);
  
  const [newMessage, setNewMessage] = useState('');
  const simulationRef = useRef<number | null>(null);
  const [isSimulationActive, setIsSimulationActive] = useState(true);
  const [minInterval, setMinInterval] = useState(5000); // 5 segundos
  const [maxInterval, setMaxInterval] = useState(15000); // 15 segundos
  const [showSettings, setShowSettings] = useState(false);
  const messageListRef = useRef<HTMLDivElement>(null);
  
  // Função para iniciar a simulação
  const startSimulation = () => {
    // Função para adicionar uma nova mensagem ao chat
    const addNewMessage = (message: ChatMessage) => {
      setMessages(prevMessages => [...prevMessages, message]);
    };
    
    // Iniciar a simulação e guardar o ID do timeout
    simulationRef.current = simulateChat(addNewMessage, minInterval, maxInterval);
  };
  
  // Função para parar a simulação
  const stopSimulation = () => {
    if (simulationRef.current !== null) {
      stopChatSimulation(simulationRef.current);
      simulationRef.current = null;
    }
  };
  
  // Iniciar ou parar a simulação quando o status mudar
  useEffect(() => {
    if (isSimulationActive) {
      startSimulation();
    } else {
      stopSimulation();
    }
    
    // Limpar a simulação quando o componente desmontar
    return () => {
      stopSimulation();
    };
  }, [isSimulationActive, minInterval, maxInterval]);
  
  // Função para lidar com a alteração do status da simulação
  const handleToggleSimulation = (active: boolean) => {
    setIsSimulationActive(active);
  };
  
  // Função para atualizar os intervalos de simulação
  const handleUpdateIntervals = (min: number, max: number) => {
    setMinInterval(min);
    setMaxInterval(max);
    
    // Reiniciar a simulação com os novos intervalos se estiver ativa
    if (isSimulationActive) {
      stopSimulation();
      startSimulation();
    }
  };
  
  // Efeito para rolar automaticamente para a mensagem mais recente
  useEffect(() => {
    if (messageListRef.current) {
      messageListRef.current.scrollTop = messageListRef.current.scrollHeight;
    }
  }, [messages]);
  
  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newMessage.trim()) return;
    
    // Adicionar a mensagem do usuário
    const userMessage: ChatMessage = {
      id: Date.now(),
      sender: 'Você',
      message: newMessage,
      timestamp: new Date()
    };
    
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setNewMessage('');
    
    // Gerar uma resposta da IA após um pequeno atraso para simular digitação
    setTimeout(() => {
      const aiResponse = generateAIResponse(newMessage, messages);
      setMessages(prevMessages => [...prevMessages, aiResponse]);
    }, 1000 + Math.random() * 2000); // Atraso entre 1-3 segundos
  };
  
  return (
    <div className="fixed top-0 right-0 h-screen w-80 flex flex-col bg-vegas-darkgray z-50 border-l border-[#33333359]">
      <ChatHeader onSettingsClick={() => setShowSettings(true)} />
      <ChatMessageList messages={messages} ref={messageListRef} />
      <ChatInput 
        newMessage={newMessage}
        setNewMessage={setNewMessage}
        handleSendMessage={handleSendMessage}
      />
      
      <Dialog open={showSettings} onOpenChange={setShowSettings}>
        <DialogContent className="bg-vegas-darkgray text-white border-vegas-gold/30">
          <DialogHeader>
            <DialogTitle>Configurações do Chat</DialogTitle>
          </DialogHeader>
          <ChatSettings 
            isSimulationActive={isSimulationActive}
            minInterval={minInterval}
            maxInterval={maxInterval}
            onToggleSimulation={handleToggleSimulation}
            onUpdateIntervals={handleUpdateIntervals}
          />
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ChatUI;
