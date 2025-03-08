export enum PlanType {
  FREE = 'free',
  BASIC = 'basic',
  PRO = 'pro',
  PREMIUM = 'premium'
}

export interface Plan {
  id: string;
  name: string;
  type: PlanType;
  description: string;
  price: number;
  interval: 'monthly' | 'annual';
  features: string[];
  // Recursos específicos que este plano permite acessar
  allowedFeatures: string[];
}

export interface UserSubscription {
  id: string;
  userId: string;
  planId: string;
  planType: PlanType;
  // Data de início da assinatura
  startDate: Date;
  // Data de término da assinatura (null para assinaturas ativas)
  endDate: Date | null;
  // Status da assinatura
  status: 'active' | 'canceled' | 'expired' | 'trial';
  // Método de pagamento usado
  paymentMethod?: string;
  // Data do próximo pagamento
  nextBillingDate?: Date;
} 