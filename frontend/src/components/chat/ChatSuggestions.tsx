import React from 'react';
import { Button } from '@/components/ui/button';

interface ChatSuggestionsProps {
  onSuggestionClick: (suggestion: string) => void;
}

const ChatSuggestions = ({ onSuggestionClick }: ChatSuggestionsProps) => {
  const suggestions = [
    'Qual roleta tá pagando melhor hoje?',
    'Alguém tem dicas pra iniciantes?',
    'Qual estratégia vocês recomendam?',
    'Qual o melhor horário pra jogar?',
    'Qual número tá saindo mais?'
  ];

  return (
    <div className="p-3 border-t border-[#33333359]">
      <p className="text-xs text-gray-400 mb-2">Sugestões:</p>
      <div className="flex flex-wrap gap-2">
        {suggestions.map((suggestion, index) => (
          <Button
            key={index}
            variant="outline"
            size="sm"
            className="text-xs py-1 px-2 h-auto bg-vegas-darkgray/50 text-vegas-gold border-vegas-gold/30 hover:bg-vegas-gold/10"
            onClick={() => onSuggestionClick(suggestion)}
          >
            {suggestion}
          </Button>
        ))}
      </div>
    </div>
  );
};

export default ChatSuggestions;
