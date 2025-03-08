/**
 * Cliente Stripe - VERSÃO TOTALMENTE SIMULADA
 * 
 * Esta versão é apenas para testes e desenvolvimento,
 * não faz chamadas para o backend ou para o Stripe.
 */

// Interface para garantir compatibilidade com o tipo real do Stripe
interface StripeClient {
  redirectToCheckout: (options: { sessionId?: string }) => Promise<{ error: any }>;
  confirmPayment: (options: any) => Promise<{ error: any }>;
}

/**
 * Cria uma sessão de checkout para um plano específico
 * VERSÃO SIMULADA - não faz chamadas reais
 * @param planId ID do plano a ser comprado
 * @param userId ID do usuário que está fazendo a compra
 */
export const createCheckoutSession = async (planId: string, userId: string): Promise<string> => {
  console.log(`[SIMULAÇÃO] Criando sessão para planId: ${planId}, userId: ${userId}`);
  
  // Simular um pequeno atraso para dar feedback ao usuário
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Retornar URL de sucesso simulada
  const sessionId = `sim_${Date.now()}_${planId}`;
  return `/payment-success?session_id=${sessionId}`;
};

/**
 * Simulação do cliente Stripe
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
    
    console.warn(
      '[Stripe Simulado] Usando implementação 100% simulada do Stripe.\n' +
      'Esta versão é apenas para testes e não faz chamadas reais.'
    );
  }
  
  return Promise.resolve(simulatedStripeInstance);
}; 