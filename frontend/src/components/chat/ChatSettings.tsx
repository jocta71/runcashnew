import React, { useState } from 'react';
import { Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Slider } from '@/components/ui/slider';

interface ChatSettingsProps {
  isSimulationActive: boolean;
  minInterval: number;
  maxInterval: number;
  onToggleSimulation: (active: boolean) => void;
  onUpdateIntervals: (min: number, max: number) => void;
}

const ChatSettings = ({
  isSimulationActive,
  minInterval,
  maxInterval,
  onToggleSimulation,
  onUpdateIntervals
}: ChatSettingsProps) => {
  const [localMinInterval, setLocalMinInterval] = useState(minInterval / 1000);
  const [localMaxInterval, setLocalMaxInterval] = useState(maxInterval / 1000);
  const [open, setOpen] = useState(false);

  const handleSave = () => {
    onUpdateIntervals(localMinInterval * 1000, localMaxInterval * 1000);
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-vegas-gold hover:text-vegas-gold/80 hover:bg-vegas-black/20">
          <Settings size={16} />
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px] bg-vegas-darkgray text-white border-vegas-gold/30">
        <DialogHeader>
          <DialogTitle>Configurações do Chat</DialogTitle>
          <DialogDescription className="text-gray-400">
            Ajuste as configurações da simulação de chat
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <div className="flex items-center justify-between">
            <Label htmlFor="simulation-toggle" className="text-white">
              Simulação de Chat
            </Label>
            <Switch
              id="simulation-toggle"
              checked={isSimulationActive}
              onCheckedChange={onToggleSimulation}
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="min-interval" className="text-white">
              Intervalo Mínimo: {localMinInterval} segundos
            </Label>
            <Slider
              id="min-interval"
              disabled={!isSimulationActive}
              min={1}
              max={30}
              step={1}
              value={[localMinInterval]}
              onValueChange={(value) => {
                const newMin = value[0];
                setLocalMinInterval(newMin);
                if (newMin > localMaxInterval) {
                  setLocalMaxInterval(newMin);
                }
              }}
              className="[&_[role=slider]]:bg-vegas-gold"
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="max-interval" className="text-white">
              Intervalo Máximo: {localMaxInterval} segundos
            </Label>
            <Slider
              id="max-interval"
              disabled={!isSimulationActive}
              min={1}
              max={60}
              step={1}
              value={[localMaxInterval]}
              onValueChange={(value) => {
                const newMax = value[0];
                setLocalMaxInterval(newMax);
                if (newMax < localMinInterval) {
                  setLocalMinInterval(newMax);
                }
              }}
              className="[&_[role=slider]]:bg-vegas-gold"
            />
          </div>
        </div>
        <DialogFooter>
          <Button 
            onClick={handleSave} 
            className="bg-vegas-gold hover:bg-vegas-gold/80 text-black"
          >
            Salvar Alterações
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export default ChatSettings;
