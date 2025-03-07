
import React from 'react';
import { Trophy, XCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface WinRateDisplayProps {
  wins: number;
  losses: number;
}

const WinRateDisplay = ({ wins, losses }: WinRateDisplayProps) => {
  const winRate = (wins / (wins + losses)) * 100;

  return (
    <div>
      <div className="space-y-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-sm">Taxa de Vitória</span>
          <span className="text-vegas-gold font-medium">{winRate.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-3 mt-2 animate-slide-up">
          <div className="flex items-center gap-1 bg-green-500/20 px-2 py-1 rounded-md transition-all duration-300 hover:bg-green-500/30 hover-scale">
            <Trophy size={16} className="text-green-500 animate-pulse" />
            <span className="text-green-500 font-medium">{wins}</span>
          </div>
          <div className="flex items-center gap-1 bg-red-500/20 px-2 py-1 rounded-md transition-all duration-300 hover:bg-red-500/30 hover-scale">
            <XCircle size={16} className="text-red-500 animate-pulse" />
            <span className="text-red-500 font-medium">{losses}</span>
          </div>
        </div>
      </div>
      <Progress
        value={winRate}
        className="h-2"
      />
    </div>
  );
};

export default WinRateDisplay;
