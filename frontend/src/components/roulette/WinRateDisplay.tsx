import React from 'react';
import { Trophy, XCircle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';

interface WinRateDisplayProps {
  wins: number;
  losses: number;
}

const WinRateDisplay = ({ wins, losses }: WinRateDisplayProps) => {
  const winRate = wins + losses > 0 ? (wins / (wins + losses)) * 100 : 0;

  return (
    <div>
      <div className="space-y-0.5 mb-1">
        <div className="flex items-center gap-1">
          <span className="text-[10px]">Taxa de Vitória</span>
          <span className="text-[#00ff00] font-medium text-[10px]">{winRate.toFixed(1)}%</span>
        </div>
        <div className="flex items-center gap-1.5 mt-0.5 animate-slide-up">
          <div className="flex items-center gap-0.5 bg-[#00ff00]/20 px-1 py-0.5 rounded-md transition-all duration-300 hover:bg-[#00ff00]/30 hover-scale">
            <Trophy size={12} className="text-[#00ff00] animate-pulse" />
            <span className="text-[#00ff00] font-medium text-[9px]">{wins}</span>
          </div>
          <div className="flex items-center gap-0.5 bg-red-500/20 px-1 py-0.5 rounded-md transition-all duration-300 hover:bg-red-500/30 hover-scale">
            <XCircle size={12} className="text-red-500 animate-pulse" />
            <span className="text-red-500 font-medium text-[9px]">{losses}</span>
          </div>
        </div>
      </div>
      <Progress
        value={winRate}
        className="h-1 bg-gray-800"
        indicatorClassName="bg-gradient-to-r from-[#00ff00] to-[#00ff00]"
      />
    </div>
  );
};

export default WinRateDisplay;
