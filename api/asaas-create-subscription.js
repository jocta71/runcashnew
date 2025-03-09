const axios = require('axios');
const { createClient } = require('@supabase/supabase-js');

module.exports = async (req, res) => {
  // Configurar CORS
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

  // Lidar com solicitações preflight
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    const { planId, customerId, userId } = req.body;
    
    // Validar dados
    if (!planId || !customerId || !userId) {
      return res.status(400).json({ error: 'Dados obrigatórios não fornecidos' });
    }

    // Mapeamento de planos
    const planDetails = {
      'free': { value: 0, name: 'Plano Gratuito RunCash' },
      'basic': { value: 19.90, name: 'Plano Básico RunCash' },
      'pro': { value: 49.90, name: 'Plano Profissional RunCash' },
      'premium': { value: 99.90, name: 'Plano Premium RunCash' }
    };

    // Verificar se o plano é gratuito
    if (planId === 'free') {
      // Configure o cliente do Supabase
      const supabaseUrl = process.env.SUPABASE_URL;
      const supabaseKey = process.env.SUPABASE_KEY;
      const supabase = createClient(supabaseUrl, supabaseKey);
      
      // Registrar assinatura gratuita diretamente no Supabase
      const { data, error } = await supabase
        .from('subscriptions')
        .upsert({
          user_id: userId,
          plan_id: 'free',
          plan_type: 'FREE',
          status: 'active',
          start_date: new Date().toISOString(),
          payment_provider: 'manual',
          payment_id: `free_${Date.now()}`
        })
        .select();
      
      if (error) {
        console.error('Erro ao criar assinatura gratuita:', error);
        throw error;
      }
      
      return res.status(200).json({
        success: true,
        subscriptionId: data[0]?.id,
        redirectUrl: `${req.headers.origin || 'https://runcashnew-frontend.vercel.app'}/payment-success?free=true`,
        message: 'Assinatura gratuita ativada com sucesso'
      });
    }

    // Calcular data de vencimento (próximo dia útil)
    const today = new Date();
    const nextDueDate = new Date(today);
    nextDueDate.setDate(today.getDate() + 1); // Próximo dia
    
    // Converter para formato YYYY-MM-DD
    const formattedDueDate = nextDueDate.toISOString().split('T')[0];

    // Criar assinatura no Asaas
    const response = await axios.post(
      'https://sandbox.asaas.com/api/v3/subscriptions',
      {
        customer: customerId,
        billingType: 'PIX', // Usar PIX como método de pagamento
        value: planDetails[planId].value,
        nextDueDate: formattedDueDate,
        cycle: 'MONTHLY',
        description: planDetails[planId].name,
        maxPayments: 12, // 12 meses
        externalReference: userId // Referência ao usuário no seu sistema
      },
      {
        headers: {
          'access_token': process.env.ASAAS_API_KEY,
          'Content-Type': 'application/json'
        }
      }
    );

    console.log('Assinatura criada com sucesso:', response.data);
    
    // Buscar informações da primeira cobrança para obter o link de pagamento
    const paymentResponse = await axios.get(
      `https://sandbox.asaas.com/api/v3/payments?subscription=${response.data.id}&status=PENDING`,
      {
        headers: {
          'access_token': process.env.ASAAS_API_KEY
        }
      }
    );
    
    let paymentUrl = null;
    if (paymentResponse.data.data && paymentResponse.data.data.length > 0) {
      // Obter link de pagamento PIX
      const paymentId = paymentResponse.data.data[0].id;
      const pixResponse = await axios.get(
        `https://sandbox.asaas.com/api/v3/payments/${paymentId}/pixQrCode`,
        {
          headers: {
            'access_token': process.env.ASAAS_API_KEY
          }
        }
      );
      
      // Obter URL de pagamento
      paymentUrl = pixResponse.data.success ? 
                  pixResponse.data.encodedImage : 
                  paymentResponse.data.data[0].invoiceUrl;
    }

    // Salvar informações da assinatura no Supabase
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_KEY;
    const supabase = createClient(supabaseUrl, supabaseKey);
    
    const planTypeMap = {
      'basic': 'BASIC',
      'pro': 'PRO',
      'premium': 'PREMIUM'
    };
    
    const { error: supabaseError } = await supabase
      .from('subscriptions')
      .upsert({
        user_id: userId,
        plan_id: planId,
        plan_type: planTypeMap[planId],
        status: 'pending',
        start_date: new Date().toISOString(),
        payment_provider: 'asaas',
        payment_id: response.data.id,
        next_billing_date: formattedDueDate
      });
    
    if (supabaseError) {
      console.error('Erro ao salvar assinatura no Supabase:', supabaseError);
    }
    
    return res.status(200).json({
      success: true,
      subscriptionId: response.data.id,
      redirectUrl: paymentUrl || response.data.invoiceUrl,
      message: 'Assinatura criada com sucesso'
    });
  } catch (error) {
    console.error('Erro ao criar assinatura no Asaas:', error.response?.data || error.message);
    return res.status(500).json({ 
      error: 'Erro ao criar assinatura', 
      details: error.response?.data || error.message 
    });
  }
}; 