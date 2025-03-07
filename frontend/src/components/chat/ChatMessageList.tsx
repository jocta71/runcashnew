import React, { forwardRef, useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage';
import { ChatMessage as ChatMessageType } from './types';

interface ChatMessageListProps {
  messages: ChatMessageType[];
}

const ChatMessageList = forwardRef<HTMLDivElement, ChatMessageListProps>(
  ({ messages }, ref) => {
    const containerRef = useRef<HTMLDivElement>(null);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    
    // Função para rolar para a mensagem mais recente
    const scrollToBottom = () => {
      if (messagesEndRef.current) {
        messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
      }
    };
    
    // Efeito para rolar para a mensagem mais recente quando novas mensagens são adicionadas
    useEffect(() => {
      scrollToBottom();
    }, [messages]);
    
    // Usar a ref passada pelo componente pai, se disponível
    const setRefs = (element: HTMLDivElement) => {
      containerRef.current = element;
      
      // Passar a ref para o componente pai, se fornecida
      if (typeof ref === 'function') {
        ref(element);
      } else if (ref) {
        ref.current = element;
      }
    };

    return (
      <div 
        ref={setRefs}
        className="flex-1 overflow-y-auto p-3 space-y-4 scrollbar-none bg-[#0b0a0f]"
      >
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        {/* Elemento invisível para rolar até o final */}
        <div ref={messagesEndRef} />
      </div>
    );
  }
);

// Adicionar displayName para o componente forwardRef
ChatMessageList.displayName = 'ChatMessageList';

export default ChatMessageList;
