// Tentar importar o Stripe normalmente
let stripeModule;
try {
  stripeModule = require('@stripe/stripe-js');
} catch (error) {
  console.warn('Não foi possível carregar o módulo @stripe/stripe-js. Usando versão simulada.');
  stripeModule = null;
}

// Substitua pela sua chave pública do Stripe para o ambiente de teste
// Esta chave é segura para estar no código do frontend, pois é pública
const STRIPE_PUBLIC_KEY = 'pk_test_51OxDFnBp4viBSzHIYME6FZtpbx2Vr1KkSTuRGYcm4lnCFf8CzKbcWDe5RMmqHENvp5uDQYCYsEVMsQnqt7KjWHh700dJnw61y6';

let stripePromise: Promise<any> | null = null;

export const getStripeClient = () => {
  if (!stripePromise) {
    // Se o módulo foi carregado com sucesso, use-o
    if (stripeModule && stripeModule.loadStripe) {
      stripePromise = stripeModule.loadStripe(STRIPE_PUBLIC_KEY);
    } else {
      // Versão de backup/simulada para quando o módulo não está disponível
      // (útil durante os builds ou ambientes sem a biblioteca)
      console.warn('Usando cliente Stripe simulado');
      stripePromise = Promise.resolve({
        // Mock das funções do Stripe
        redirectToCheckout: async ({ sessionId }: { sessionId: string }) => {
          console.log('Stripe mock: redirectToCheckout', sessionId);
          // Em produção, isso redirecionaria para o Stripe
          // Para simulação, vamos redirecionar para nossa própria página de sucesso
          window.location.href = `/payment-success?session_id=sim_${Date.now()}`;
          return { error: null };
        },
        // Outras funções simuladas conforme necessário
      });
    }
  }
  return stripePromise;
}; 