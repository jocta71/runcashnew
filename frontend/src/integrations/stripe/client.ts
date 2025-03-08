import { loadStripe } from '@stripe/stripe-js';

// Substitua pela sua chave pública do Stripe para o ambiente de teste
// Esta chave é segura para estar no código do frontend, pois é pública
const STRIPE_PUBLIC_KEY = 'pk_test_51OxDFnBp4viBSzHIYME6FZtpbx2Vr1KkSTuRGYcm4lnCFf8CzKbcWDe5RMmqHENvp5uDQYCYsEVMsQnqt7KjWHh700dJnw61y6';

let stripePromise: Promise<any> | null = null;

export const getStripeClient = () => {
  if (!stripePromise) {
    stripePromise = loadStripe(STRIPE_PUBLIC_KEY);
  }
  return stripePromise;
}; 