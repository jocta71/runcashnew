import { useState } from 'react';
import { useSubscription } from '@/context/SubscriptionContext';
import { PlanType } from '@/types/plans';
import { Check, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { 
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { createCheckoutSession } from '@/integrations/stripe/client';
import { useAuth } from '@/context/AuthContext';

const PlansPage = () => {
  const { availablePlans, currentPlan, upgradePlan, loading } = useSubscription();
  const { user } = useAuth();
  const [selectedInterval, setSelectedInterval] = useState<'monthly' | 'annual'>('monthly');
  const [processingPlanId, setProcessingPlanId] = useState<string | null>(null);
  const { toast } = useToast();
  
  const handleSelectPlan = async (planId: string) => {
    if (loading || !user) return;
    
    // Se já for o plano atual
    if (currentPlan?.id === planId) {
      toast({
        title: "Plano já ativo",
        description: "Você já está inscrito neste plano.",
      });
      return;
    }
    
    try {
      setProcessingPlanId(planId);
      
      if (planId === 'free') {
        // Para o plano gratuito, usar a função existente upgradePlan
        await upgradePlan(planId);
        toast({
          title: "Plano gratuito ativado",
          description: "Você agora está usando o plano gratuito.",
        });
      } else {
        // Para planos pagos, criar uma sessão de checkout
        const checkoutUrl = await createCheckoutSession(planId, user.id);
        // Redirecionar para a página de checkout do Stripe
        window.location.href = checkoutUrl;
      }
    } catch (error) {
      console.error("Erro ao atualizar plano:", error);
      toast({
        title: "Erro ao processar pagamento",
        description: "Não foi possível processar seu pagamento. Tente novamente.",
        variant: "destructive"
      });
    } finally {
      setProcessingPlanId(null);
    }
  };
  
  // Calcular preço anual (com desconto)
  const getAnnualPrice = (monthlyPrice: number) => {
    // 20% de desconto no plano anual
    return (monthlyPrice * 12 * 0.8).toFixed(2);
  };

  return (
    <div className="container mx-auto py-12 px-4">
      <div className="text-center mb-12">
        <h1 className="text-3xl font-bold mb-4">Escolha o plano ideal para você</h1>
        <p className="text-gray-400 max-w-2xl mx-auto">
          Desbloqueie recursos avançados e melhore sua experiência de jogo com nossos planos premium.
          Cancele a qualquer momento.
        </p>
        
        {/* Alternar entre mensal e anual */}
        <div className="flex items-center justify-center mt-8 space-x-2">
          <div 
            className={`px-4 py-2 rounded-l-md cursor-pointer ${
              selectedInterval === 'monthly' 
                ? 'bg-vegas-gold text-black font-medium' 
                : 'bg-vegas-darkgray text-gray-300'
            }`}
            onClick={() => setSelectedInterval('monthly')}
          >
            Mensal
          </div>
          <div 
            className={`px-4 py-2 rounded-r-md cursor-pointer ${
              selectedInterval === 'annual' 
                ? 'bg-vegas-gold text-black font-medium' 
                : 'bg-vegas-darkgray text-gray-300'
            }`}
            onClick={() => setSelectedInterval('annual')}
          >
            Anual <span className="text-xs">(-20%)</span>
          </div>
        </div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-7xl mx-auto">
        {availablePlans.map((plan) => {
          const isCurrentPlan = currentPlan?.id === plan.id;
          const isProcessing = processingPlanId === plan.id;
          const displayPrice = selectedInterval === 'monthly' 
            ? plan.price 
            : getAnnualPrice(plan.price);
          
          return (
            <div 
              key={plan.id}
              className={`bg-vegas-darkgray rounded-xl overflow-hidden border ${
                isCurrentPlan 
                  ? 'border-vegas-gold' 
                  : 'border-gray-700'
              }`}
            >
              {/* Cabeçalho do plano */}
              <div className={`p-6 ${
                plan.type === PlanType.PREMIUM 
                  ? 'bg-gradient-to-r from-vegas-gold to-yellow-500' 
                  : 'bg-vegas-black'
              }`}>
                <h3 className={`text-xl font-bold ${
                  plan.type === PlanType.PREMIUM ? 'text-black' : 'text-white'
                }`}>
                  {plan.name}
                </h3>
                <p className={`text-sm ${
                  plan.type === PlanType.PREMIUM ? 'text-black/70' : 'text-gray-400'
                }`}>
                  {plan.description}
                </p>
              </div>
              
              {/* Preço */}
              <div className="p-6 border-b border-gray-700">
                <div className="flex items-baseline">
                  {plan.type !== PlanType.FREE && (
                    <>
                      <span className="text-3xl font-bold">
                        R${displayPrice}
                      </span>
                      <span className="text-gray-400 ml-1 text-sm">
                        /{selectedInterval === 'monthly' ? 'mês' : 'ano'}
                      </span>
                    </>
                  )}
                  {plan.type === PlanType.FREE && (
                    <span className="text-3xl font-bold">Grátis</span>
                  )}
                </div>
                
                {/* Botão */}
                <Button 
                  className={`w-full mt-4 ${
                    plan.type === PlanType.PREMIUM 
                      ? 'bg-vegas-gold hover:bg-vegas-gold/80 text-black' 
                      : isCurrentPlan 
                        ? 'bg-green-600 hover:bg-green-700' 
                        : ''
                  }`}
                  onClick={() => handleSelectPlan(plan.id)}
                  disabled={isCurrentPlan || isProcessing || loading}
                >
                  {isProcessing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                  {isCurrentPlan ? 'Plano Atual' : 'Selecionar Plano'}
                </Button>
              </div>
              
              {/* Lista de recursos */}
              <div className="p-6">
                <h4 className="font-medium mb-4">Inclui:</h4>
                <ul className="space-y-3">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="flex items-start">
                      <Check className="h-5 w-5 text-green-500 mr-2 shrink-0" />
                      <span className="text-sm text-gray-300">{feature}</span>
                    </li>
                  ))}
                </ul>
              </div>
              
              {/* Badge do plano atual */}
              {isCurrentPlan && (
                <div className="bg-green-600 py-2 text-center text-sm font-medium">
                  Seu plano atual
                </div>
              )}
            </div>
          );
        })}
      </div>
      
      {/* Informação sobre pagamentos */}
      <div className="max-w-7xl mx-auto mt-12 p-4 bg-vegas-darkgray rounded-lg border border-gray-700">
        <div className="flex items-center space-x-2 text-sm text-gray-400">
          <AlertCircle className="h-4 w-4" />
          <p>
            Todos os pagamentos são processados de forma segura via Stripe. 
            Você pode cancelar sua assinatura a qualquer momento.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PlansPage; 