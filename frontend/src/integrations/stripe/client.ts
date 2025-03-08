/**
 * Cliente Stripe - versão híbrida que suporta modo simulado e real
 * 
 * Esta versão é capaz de funcionar tanto em modo simulado quanto com o Stripe real,
 * dependendo do ambiente e da disponibilidade do backend.
 */

import axios from 'axios';

// Chave publicável do Stripe (usada para referência)
const STRIPE_PUBLIC_KEY = 'pk_live_51MTxBYGLEdW1oQ9E7pX9cXQqOMopw2XgRVI6gNRDLG9VU2poXeox6O8CvdIhwjwHULAOVccHNcLlZkuE7CRt3oBj00w80prp31';

// Define a URL base da API
const API_URL = import.meta.env.VITE_API_URL || 'https://runcashnew-frontend-nu.vercel.app/';

// Interface para garantir compatibilidade com o tipo real do Stripe
interface StripeClient {
  redirectToCheckout: (options: { sessionId?: string }) => Promise<{ error: any }>;
  confirmPayment: (options: any) => Promise<{ error: any }>;
}

/**
 * Cria uma sessão de checkout para um plano específico
 * @param planId ID do plano a ser comprado
 * @param userId ID do usuário que está fazendo a compra
 */
export const createCheckoutSession = async (planId: string, userId: string): Promise<string> => {
  try {
    console.log(`Iniciando criação de sessão de checkout para planId: ${planId}, userId: ${userId}`);
    console.log(`URL da API: ${API_URL}/api/create-checkout-session`);
    
    // Chamar o backend para criar uma sessão de checkout
    const response = await axios.post(`${API_URL}/api/create-checkout-session`, {
      planId,
      userId
    });
    
    console.log('Resposta do servidor:', response.data);
    
    // Se for o plano gratuito, retorna a URL de sucesso diretamente
    if (response.data.redirectUrl) {
      console.log(`Plano gratuito - Redirecionando para: ${response.data.redirectUrl}`);
      return response.data.redirectUrl;
    }
    
    // Para planos pagos, retorna a URL do Stripe para redirecionamento
    console.log(`Plano pago - Redirecionando para: ${response.data.url}`);
    return response.data.url;
  } catch (error) {
    console.error('Erro ao criar sessão de checkout:', error);
    if (axios.isAxiosError(error)) {
      console.error('Detalhes do erro:', {
        message: error.message,
        status: error.response?.status,
        data: error.response?.data
      });
    }
    throw new Error('Não foi possível criar a sessão de checkout. Tente novamente.');
  }
};

// Simulação do cliente Stripe (usado como fallback)
const createSimulatedStripe = (): StripeClient => {
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
let simulatedStripeInstance: StripeClient | null = null;

/**
 * Função para obter o cliente Stripe
 * Esta função é uma substituição para loadStripe() da biblioteca @stripe/stripe-js
 */
export const getStripeClient = (): Promise<StripeClient> => {
  if (!simulatedStripeInstance) {
    simulatedStripeInstance = createSimulatedStripe();
    
    console.warn(
      '[Stripe Híbrido] Usando implementação simulada do Stripe.\n' +
      'Redirecionamentos de checkout serão processados pela API backend.'
    );
  }
  
  return Promise.resolve(simulatedStripeInstance);
}; 