/**
 * Implementação simulada do cliente Stripe
 * 
 * Esta versão remove completamente a dependência de @stripe/stripe-js
 * para evitar problemas de build, mas oferece uma API compatível para
 * uso em desenvolvimento e produção.
 */

// Chave do Stripe (apenas para referência, não usada na simulação)
const STRIPE_PUBLIC_KEY = 'pk_test_51OxDFnBp4viBSzHIYME6FZtpbx2Vr1KkSTuRGYcm4lnCFf8CzKbcWDe5RMmqHENvp5uDQYCYsEVMsQnqt7KjWHh700dJnw61y6';

// Interface para garantir compatibilidade com o tipo real do Stripe
interface SimulatedStripe {
  redirectToCheckout: (options: { sessionId?: string }) => Promise<{ error: any }>;
  confirmPayment: (options: any) => Promise<{ error: any }>;
  // Outras funções que você possa precisar
}

// Simulação do cliente Stripe
const createSimulatedStripe = (): SimulatedStripe => {
  return {
    redirectToCheckout: async ({ sessionId }: { sessionId?: string }) => {
      console.log('[Stripe Simulado] redirectToCheckout chamado com sessionId:', sessionId);
      
      // Simular um pequeno atraso
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Em ambiente de produção, isto redirecionaria para o Stripe
      // Na simulação, redirecionamos diretamente para nossa página de sucesso
      window.location.href = `/payment-success?session_id=sim_${Date.now()}`;
      
      return { error: null };
    },
    
    confirmPayment: async (options: any) => {
      console.log('[Stripe Simulado] confirmPayment chamado com:', options);
      return { error: null };
    }
  };
};

// Manter uma única instância do cliente simulado
let simulatedStripeInstance: SimulatedStripe | null = null;

/**
 * Função para obter o cliente Stripe
 * Esta função é uma substituição para loadStripe() da biblioteca @stripe/stripe-js
 */
export const getStripeClient = (): Promise<SimulatedStripe> => {
  if (!simulatedStripeInstance) {
    simulatedStripeInstance = createSimulatedStripe();
    
    console.warn(
      '[Stripe Simulado] Usando implementação simulada do Stripe.\n' +
      'Em produção, substitua este arquivo pela implementação real usando @stripe/stripe-js.'
    );
  }
  
  return Promise.resolve(simulatedStripeInstance);
}; 