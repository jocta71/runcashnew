import { 
  Bell, User, Wallet, Settings, LogOut, Info, ChevronDown, Menu, TrendingUp, Trophy, Flame,
  ArrowLeft, ArrowRight, Search
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import { useState, useEffect } from "react";

interface NavbarProps {
  topRoulettes?: {
    name: string;
    wins: number;
    losses: number;
  }[];
}

const Navbar = ({ topRoulettes = [] }: NavbarProps) => {
  const [currentView, setCurrentView] = useState<'hot' | 'trending' | 'new'>('hot');
  const [isAnimating, setIsAnimating] = useState(false);

  const rotateView = (direction: 'next' | 'prev') => {
    setIsAnimating(true);
    setTimeout(() => {
      if (direction === 'next') {
        if (currentView === 'hot') setCurrentView('trending');
        else if (currentView === 'trending') setCurrentView('new');
        else setCurrentView('hot');
      } else {
        if (currentView === 'hot') setCurrentView('new');
        else if (currentView === 'trending') setCurrentView('hot');
        else setCurrentView('trending');
      }
      setIsAnimating(false);
    }, 300);
  };

  useEffect(() => {
    const timer = setInterval(() => {
      rotateView('next');
    }, 10000);
    
    return () => clearInterval(timer);
  }, [currentView]);

  const viewData = {
    hot: {
      title: "Hot Roletas",
      icon: <TrendingUp size={18} className="text-vegas-green" />,
      data: topRoulettes
    },
    trending: {
      title: "Tendências",
      icon: <Flame size={18} className="text-vegas-gold" />,
      data: topRoulettes.sort((a, b) => (b.wins - b.losses) - (a.wins - a.losses))
    },
    new: {
      title: "Novas Roletas",
      icon: <Trophy size={18} className="text-vegas-blue" />,
      data: [...topRoulettes].sort(() => Math.random() - 0.5)
    }
  };

  return (
    <div className="fixed top-0 z-30 left-64 right-0 h-16 bg-vegas-darkgray border-b border-border flex items-center justify-between px-4">
      <div className="flex items-center gap-4">
        <span className="text-2xl font-bold text-vegas-green">Vega</span>
        <div className="relative w-8 h-8 flex items-center justify-center rounded-full ml-2">
          <Search size={16} className="text-gray-400" />
        </div>
      </div>
      
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-1 bg-blue-900/30 py-1 px-3 rounded-full">
          <span className="text-white text-xs font-medium">₱342,203,561.23</span>
          <ChevronDown size={14} className="text-gray-400" />
        </div>
        
        <Button variant="default" size="sm" className="h-8 bg-vegas-green text-black font-medium">
          <Wallet size={15} className="mr-1" />
          Wallet
        </Button>
      </div>
      
      <div className="flex items-center gap-3">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="rounded-full h-8 w-8 p-0">
              <Avatar className="h-8 w-8 border-2 border-gray-700">
                <AvatarImage src="https://github.com/shadcn.png" alt="@user" />
                <AvatarFallback>CN</AvatarFallback>
              </Avatar>
              <ChevronDown size={12} className="text-gray-400 absolute bottom-0 right-0" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-48 bg-vegas-darkgray">
            <DropdownMenuItem>
              <User size={16} className="mr-2" /> Perfil
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings size={16} className="mr-2" /> Configurações
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Wallet size={16} className="mr-2" /> Depósito
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem className="text-vegas-red">
              <LogOut size={16} className="mr-2" /> Sair
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
        
        <Button variant="ghost" size="icon" className="relative h-8 w-8 rounded-full bg-vegas-green/10">
          <Bell size={16} className="text-vegas-green" />
          <span className="absolute -top-1 -right-1 w-4 h-4 bg-vegas-green rounded-full text-[10px] flex items-center justify-center text-black font-bold">
            3
          </span>
        </Button>
        
        <Button
          variant="ghost"
          size="sm"
          className="flex items-center gap-1 h-8 text-xs text-white bg-vegas-darkgray/80 border border-gray-700"
        >
          <Info size={14} />
          Rules
        </Button>
        
        <div className="flex items-center gap-1 bg-vegas-green/10 rounded-lg py-1 px-2">
          <Trophy size={16} className="text-vegas-green" />
          <span className="text-vegas-green text-xs font-bold">3,281</span>
        </div>
        
        <Button variant="ghost" size="icon" className="h-8 w-8 rounded-full bg-vegas-darkgray/80">
          <div className="flex flex-col gap-1">
            <div className="w-3 h-0.5 bg-gray-400"></div>
            <div className="w-3 h-0.5 bg-gray-400"></div>
            <div className="w-3 h-0.5 bg-gray-400"></div>
          </div>
        </Button>
      </div>
    </div>
  );
};

export default Navbar;
