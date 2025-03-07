import React from 'react';
import { Dices, Play, Eye, EyeOff, WandSparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';

interface RouletteActionButtonsProps {
  toggleSuggestions: () => void;
  toggleBlur: () => void;
  isBlurred: boolean;
  showSuggestions: boolean;
  handlePlay: (e: React.MouseEvent) => void;
}

const RouletteActionButtons = ({ 
  toggleSuggestions, 
  toggleBlur, 
  isBlurred, 
  showSuggestions, 
  handlePlay 
}: RouletteActionButtonsProps) => {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex justify-end gap-2">
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button 
                variant="ghost" 
                size="icon" 
                className="h-8 w-8 text-vegas-gold hover:text-vegas-gold/80 hover:bg-vegas-black/20"
                onClick={toggleSuggestions}
              >
                <WandSparkles size={16} />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{showSuggestions ? "Ocultar sugestões" : "Mostrar sugestões"}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>

        {showSuggestions && (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-8 w-8 text-vegas-gold hover:text-vegas-gold/80 hover:bg-vegas-black/20"
                  onClick={toggleBlur}
                >
                  {isBlurred ? <EyeOff size={16} /> : <Eye size={16} />}
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{isBlurred ? "Mostrar números" : "Ocultar números"}</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </div>
      
      <div className="flex gap-2">
        <Button 
          className="flex-1 bg-[#00baff] hover:bg-[#00baff]/80 text-black font-medium"
          onClick={(e) => {
            e.stopPropagation(); // Evita que o clique propague para o card
          }}
        >
          <Dices size={16} className="mr-2" />
          Ver Detalhes
        </Button>
        
        <Button 
          className="flex-1 text-black font-medium animate-pulse-neon bg-gradient-to-b from-[#00ff00] to-[#34db53] hover:from-[#00ff00]/90 hover:to-[#34db53]/90"
          onClick={handlePlay}
        >
          <Play size={16} className="mr-2" />
          Ir para a Roleta
        </Button>
      </div>
    </div>
  );
};

export default React.memo(RouletteActionButtons);
