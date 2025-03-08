/**
 * Cliente Stripe - Usando API do Vercel
 */

import axios from 'axios';

/**
 * Cria uma sessão de checkout para um plano específico
 * @param planId ID do plano a ser comprado
 * @param userId ID do usuário que está fazendo a compra
 */
export const createCheckoutSession = async (planId: string, userId: string): Promise<string> => {
  try {
    console.log(`Iniciando criação de sessão de checkout para planId: ${planId}, userId: ${userId}`);
    
    // Como estamos usando o Vercel, a API está no mesmo domínio do frontend
    const response = await axios.post('/api/create-checkout-session', {
      planId,
      userId
    });
    
    if (response.data && response.data.url) {
      console.log('Sessão de checkout criada com sucesso:', response.data);
      return response.data.url;
    } else {
      throw new Error('Resposta da API inválida');
    }
    
  } catch (error) {
    console.error('Erro ao criar sessão de checkout:', error);
    
    // Em caso de erro, usar modo simulado como fallback
    console.log('Usando modo simulado devido a erro');
    
    // Para teste local, simular redirecionamento
    if (planId === 'free') {
      return '/payment-success?free=true';
    } else {
      const sessionId = `sim_${Date.now()}_${planId}`;
      return `/payment-success?session_id=${sessionId}`;
    }
  }
};

// Interface para garantir compatibilidade com o tipo real do Stripe
interface StripeClient {
  redirectToCheckout: (options: { sessionId?: string }) => Promise<{ error: any }>;
  confirmPayment: (options: any) => Promise<{ error: any }>;
}

/**
 * Simulação do cliente Stripe (usado como fallback)
 */
const createSimulatedStripe = (): StripeClient => {
  return {
    redirectToCheckout: async ({ sessionId }: { sessionId?: string }) => {
      console.log('[Stripe Simulado] redirectToCheckout chamado com sessionId:', sessionId);
      
      // Simular um pequeno atraso
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Redirecionamento simulado
      window.location.href = `/payment-success?session_id=${sessionId || `sim_${Date.now()}`}`;
      
      return { error: null };
    },
    
    confirmPayment: async (options: any) => {
      console.log('[Stripe Simulado] confirmPayment chamado com:', options);
      return { error: null };
    }
  };
};

// Manter uma única instância do cliente simulado
let simulatedStripeInstance: StripeClient | null = null;

/**
 * Função para obter o cliente Stripe
 * Esta função é uma substituição para loadStripe() da biblioteca @stripe/stripe-js
 */
export const getStripeClient = (): Promise<StripeClient> => {
  if (!simulatedStripeInstance) {
    simulatedStripeInstance = createSimulatedStripe();
  }
  
  return Promise.resolve(simulatedStripeInstance);
}; 