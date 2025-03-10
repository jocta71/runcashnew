import React from 'react';
import { Dices, Play } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface RouletteActionButtonsProps {
  onDetailsClick: (e: React.MouseEvent) => void;
  onPlayClick: (e: React.MouseEvent) => void;
}

const RouletteActionButtons = ({ onDetailsClick, onPlayClick }: RouletteActionButtonsProps) => {
  return (
    <div className="flex flex-col sm:flex-row gap-1 mt-1 flex-shrink-0">
      <Button 
        onClick={onDetailsClick}
        className="w-full sm:flex-1 bg-[#00baff] hover:bg-[#00baff]/80 text-black font-medium text-xs py-1.5 h-auto"
      >
        <Dices size={14} className="mr-1" />
        Ver Página de Estatísticas
      </Button>
      
      <Button 
        className="w-full sm:flex-1 text-black font-medium animate-pulse-neon bg-gradient-to-b from-[#00ff00] to-[#8bff00] hover:from-[#00ff00]/90 hover:to-[#8bff00]/90 text-xs py-1.5 h-auto truncate"
        onClick={onPlayClick}
      >
        <Play size={14} className="mr-1 shrink-0" />
        <span className="truncate">Ir para a Roleta</span>
      </Button>
    </div>
  );
};

export default RouletteActionButtons;
