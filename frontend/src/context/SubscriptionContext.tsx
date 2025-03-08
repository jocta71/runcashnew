import React, { createContext, useContext, useEffect, useState } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { Plan, PlanType, UserSubscription } from '@/types/plans';
import { useAuth } from './AuthContext';
import { useToast } from '@/hooks/use-toast';

// Lista de planos disponíveis
export const availablePlans: Plan[] = [
  {
    id: 'free',
    name: 'Free',
    type: PlanType.FREE,
    description: 'Acesso básico para experimentar a plataforma',
    price: 0,
    interval: 'monthly',
    features: [
      'Acesso a estatísticas básicas',
      'Visualização de até 5 roletas',
      'Atualizações a cada 10 minutos'
    ],
    allowedFeatures: ['view_basic_stats', 'view_limited_roulettes']
  },
  {
    id: 'basic',
    name: 'Básico',
    type: PlanType.BASIC,
    description: 'Plano ideal para iniciantes',
    price: 19.90,
    interval: 'monthly',
    features: [
      'Acesso a estatísticas padrão',
      'Visualização de até 15 roletas',
      'Atualizações a cada 5 minutos',
      'Suporte por email'
    ],
    allowedFeatures: ['view_basic_stats', 'view_standard_roulettes', 'email_support']
  },
  {
    id: 'pro',
    name: 'Profissional',
    type: PlanType.PRO,
    description: 'Para jogadores que querem levar o jogo a sério',
    price: 49.90,
    interval: 'monthly',
    features: [
      'Acesso a estatísticas avançadas',
      'Visualização de roletas ilimitadas',
      'Atualizações a cada 1 minuto',
      'Suporte prioritário',
      'Alertas personalizados'
    ],
    allowedFeatures: ['view_advanced_stats', 'view_unlimited_roulettes', 'priority_support', 'custom_alerts']
  },
  {
    id: 'premium',
    name: 'Premium',
    type: PlanType.PREMIUM,
    description: 'Experiência completa para profissionais',
    price: 99.90,
    interval: 'monthly',
    features: [
      'Acesso a estatísticas em tempo real',
      'Visualização de roletas ilimitadas',
      'Atualizações em tempo real',
      'Suporte VIP 24/7',
      'Alertas avançados personalizados',
      'Estratégias exclusivas',
      'Acesso antecipado a novas funcionalidades'
    ],
    allowedFeatures: [
      'view_realtime_stats', 
      'view_unlimited_roulettes', 
      'vip_support', 
      'advanced_alerts', 
      'exclusive_strategies', 
      'early_access'
    ]
  }
];

interface SubscriptionContextType {
  currentSubscription: UserSubscription | null;
  currentPlan: Plan | null;
  availablePlans: Plan[];
  loading: boolean;
  hasFeatureAccess: (featureId: string) => boolean;
  upgradePlan: (planId: string) => Promise<void>;
  cancelSubscription: () => Promise<void>;
}

const SubscriptionContext = createContext<SubscriptionContextType | undefined>(undefined);

export const SubscriptionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  const { toast } = useToast();
  const [currentSubscription, setCurrentSubscription] = useState<UserSubscription | null>(null);
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null);
  const [loading, setLoading] = useState(true);

  // Carrega a assinatura do usuário quando ele faz login
  useEffect(() => {
    const loadUserSubscription = async () => {
      if (!user) {
        setCurrentSubscription(null);
        setCurrentPlan(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        // Buscar a assinatura do usuário no Supabase
        const { data, error } = await supabase
          .from('subscriptions')
          .select('*')
          .eq('user_id', user.id)
          .eq('status', 'active')
          .single();

        if (error) {
          console.error('Erro ao carregar assinatura:', error);
          // Se não encontrar assinatura, definir o plano gratuito como padrão
          setCurrentSubscription(null);
          setCurrentPlan(availablePlans.find(plan => plan.type === PlanType.FREE) || null);
        } else if (data) {
          // Converter dados do banco para o formato da interface
          const subscription: UserSubscription = {
            id: data.id,
            userId: data.user_id,
            planId: data.plan_id,
            planType: data.plan_type as PlanType,
            startDate: new Date(data.start_date),
            endDate: data.end_date ? new Date(data.end_date) : null,
            status: data.status,
            paymentMethod: data.payment_method,
            nextBillingDate: data.next_billing_date ? new Date(data.next_billing_date) : undefined
          };
          
          setCurrentSubscription(subscription);
          
          // Encontrar o plano correspondente
          const plan = availablePlans.find(p => p.id === subscription.planId);
          setCurrentPlan(plan || availablePlans.find(p => p.type === PlanType.FREE) || null);
        } else {
          // Se não encontrar assinatura, definir o plano gratuito como padrão
          setCurrentSubscription(null);
          setCurrentPlan(availablePlans.find(plan => plan.type === PlanType.FREE) || null);
        }
      } catch (err) {
        console.error('Erro ao carregar dados da assinatura:', err);
        // Em caso de erro, definir o plano gratuito como padrão
        setCurrentSubscription(null);
        setCurrentPlan(availablePlans.find(plan => plan.type === PlanType.FREE) || null);
      } finally {
        setLoading(false);
      }
    };

    loadUserSubscription();
  }, [user]);

  // Verificar se o usuário tem acesso a um recurso específico
  const hasFeatureAccess = (featureId: string): boolean => {
    if (!currentPlan) return false;
    return currentPlan.allowedFeatures.includes(featureId);
  };

  // Função para atualizar o plano
  const upgradePlan = async (planId: string): Promise<void> => {
    if (!user) {
      toast({
        title: "Erro ao atualizar plano",
        description: "Você precisa estar logado para atualizar seu plano.",
        variant: "destructive"
      });
      return;
    }

    setLoading(true);
    try {
      // Encontrar o plano selecionado
      const selectedPlan = availablePlans.find(p => p.id === planId);
      if (!selectedPlan) {
        throw new Error("Plano não encontrado");
      }

      // Aqui você implementaria a integração com gateway de pagamento
      // Por enquanto, simularemos uma atualização direta no banco

      // Verificar se já existe uma assinatura ativa
      if (currentSubscription) {
        // Atualizar assinatura existente
        const { error } = await supabase
          .from('subscriptions')
          .update({
            plan_id: selectedPlan.id,
            plan_type: selectedPlan.type,
            status: 'active',
            updated_at: new Date().toISOString(),
            next_billing_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString() // +30 dias
          })
          .eq('id', currentSubscription.id);

        if (error) throw error;
      } else {
        // Criar nova assinatura
        const { error } = await supabase
          .from('subscriptions')
          .insert({
            user_id: user.id,
            plan_id: selectedPlan.id,
            plan_type: selectedPlan.type,
            start_date: new Date().toISOString(),
            status: 'active',
            next_billing_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString() // +30 dias
          });

        if (error) throw error;
      }

      // Atualizar estado local
      const newSubscription: UserSubscription = {
        id: currentSubscription?.id || `sub_${Date.now()}`,
        userId: user.id,
        planId: selectedPlan.id,
        planType: selectedPlan.type,
        startDate: new Date(),
        endDate: null,
        status: 'active',
        nextBillingDate: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000) // +30 dias
      };

      setCurrentSubscription(newSubscription);
      setCurrentPlan(selectedPlan);

      toast({
        title: "Plano atualizado com sucesso",
        description: `Seu plano foi atualizado para ${selectedPlan.name}.`,
      });
    } catch (error) {
      console.error('Erro ao atualizar plano:', error);
      toast({
        title: "Erro ao atualizar plano",
        description: error.message || "Ocorreu um erro ao atualizar seu plano. Tente novamente.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  // Função para cancelar a assinatura
  const cancelSubscription = async (): Promise<void> => {
    if (!user || !currentSubscription) {
      toast({
        title: "Erro ao cancelar assinatura",
        description: "Você não possui uma assinatura ativa para cancelar.",
        variant: "destructive"
      });
      return;
    }

    setLoading(true);
    try {
      // Atualizar status da assinatura para cancelado
      const { error } = await supabase
        .from('subscriptions')
        .update({
          status: 'canceled',
          end_date: new Date().toISOString(),
          updated_at: new Date().toISOString()
        })
        .eq('id', currentSubscription.id);

      if (error) throw error;

      // Atualizar estado local
      const freePlan = availablePlans.find(plan => plan.type === PlanType.FREE);
      setCurrentSubscription(null);
      setCurrentPlan(freePlan || null);

      toast({
        title: "Assinatura cancelada",
        description: "Sua assinatura foi cancelada com sucesso. Você agora está no plano gratuito.",
      });
    } catch (error) {
      console.error('Erro ao cancelar assinatura:', error);
      toast({
        title: "Erro ao cancelar assinatura",
        description: error.message || "Ocorreu um erro ao cancelar sua assinatura. Tente novamente.",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const value = {
    currentSubscription,
    currentPlan,
    availablePlans,
    loading,
    hasFeatureAccess,
    upgradePlan,
    cancelSubscription
  };

  return <SubscriptionContext.Provider value={value}>{children}</SubscriptionContext.Provider>;
};

export const useSubscription = () => {
  const context = useContext(SubscriptionContext);
  if (context === undefined) {
    throw new Error('useSubscription must be used within a SubscriptionProvider');
  }
  return context;
}; 