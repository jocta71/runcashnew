const { createClient } = require('@supabase/supabase-js');

module.exports = async (req, res) => {
  // Configurar CORS
  res.setHeader('Access-Control-Allow-Credentials', true);
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,OPTIONS,PATCH,DELETE,POST,PUT');
  res.setHeader('Access-Control-Allow-Headers', 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version');

  // Responder a requisições preflight
  if (req.method === 'OPTIONS') {
    return res.status(200).end();
  }

  // Para requisições GET (verificação do webhook)
  if (req.method === 'GET') {
    return res.status(200).json({ status: 'Webhook endpoint ativo. Use POST para eventos do Asaas.' });
  }

  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method Not Allowed' });
  }

  try {
    const webhookData = req.body;
    console.log('Evento recebido do Asaas:', webhookData);
    
    // Validar assinatura do webhook (opcional, mas recomendado)
    // const webhookSignature = req.headers['asaas-signature'];
    // const webhookSecret = process.env.ASAAS_WEBHOOK_SECRET;
    // Implementar validação de segurança se necessário
    
    // Configure o cliente do Supabase
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_KEY;
    const supabase = createClient(supabaseUrl, supabaseKey);
    
    // Processar diferentes tipos de eventos
    const eventType = webhookData.event;
    const payment = webhookData.payment;
    
    if (!payment) {
      return res.status(400).json({ error: 'Dados de pagamento não fornecidos' });
    }
    
    // Obter ID da assinatura do pagamento
    const subscriptionId = payment.subscription;
    
    if (!subscriptionId) {
      console.log('Pagamento não relacionado a uma assinatura', payment);
      return res.status(200).json({ message: 'Evento ignorado - não é uma assinatura' });
    }
    
    // Buscar assinatura no Supabase
    const { data: subscriptionData, error: fetchError } = await supabase
      .from('subscriptions')
      .select('*')
      .eq('payment_id', subscriptionId)
      .single();
    
    if (fetchError || !subscriptionData) {
      console.error('Assinatura não encontrada no banco de dados:', subscriptionId);
      return res.status(404).json({ error: 'Assinatura não encontrada' });
    }
    
    // Processar eventos
    switch (eventType) {
      case 'PAYMENT_CONFIRMED': {
        // Atualizar assinatura para ativa quando o pagamento é confirmado
        const { error: updateError } = await supabase
          .from('subscriptions')
          .update({ 
            status: 'active',
            updated_at: new Date().toISOString() 
          })
          .eq('id', subscriptionData.id);
        
        if (updateError) {
          console.error('Erro ao atualizar status da assinatura:', updateError);
          return res.status(500).json({ error: 'Erro ao atualizar assinatura' });
        }
        
        console.log(`Assinatura ${subscriptionData.id} ativada com sucesso`);
        break;
      }
      
      case 'PAYMENT_RECEIVED': {
        // Similar ao PAYMENT_CONFIRMED
        const { error: updateError } = await supabase
          .from('subscriptions')
          .update({ 
            status: 'active',
            updated_at: new Date().toISOString() 
          })
          .eq('id', subscriptionData.id);
        
        if (updateError) {
          console.error('Erro ao atualizar status da assinatura:', updateError);
          return res.status(500).json({ error: 'Erro ao atualizar assinatura' });
        }
        
        console.log(`Pagamento recebido para assinatura ${subscriptionData.id}`);
        break;
      }
      
      case 'PAYMENT_OVERDUE': {
        // Atualizar assinatura para atrasada
        const { error: updateError } = await supabase
          .from('subscriptions')
          .update({ 
            status: 'overdue',
            updated_at: new Date().toISOString() 
          })
          .eq('id', subscriptionData.id);
        
        if (updateError) {
          console.error('Erro ao atualizar status da assinatura:', updateError);
          return res.status(500).json({ error: 'Erro ao atualizar assinatura' });
        }
        
        console.log(`Assinatura ${subscriptionData.id} marcada como atrasada`);
        break;
      }
      
      case 'PAYMENT_DELETED':
      case 'PAYMENT_REFUNDED':
      case 'PAYMENT_REFUND_REQUESTED': {
        // Cancelar assinatura
        const { error: updateError } = await supabase
          .from('subscriptions')
          .update({ 
            status: 'canceled',
            end_date: new Date().toISOString(),
            updated_at: new Date().toISOString() 
          })
          .eq('id', subscriptionData.id);
        
        if (updateError) {
          console.error('Erro ao cancelar assinatura:', updateError);
          return res.status(500).json({ error: 'Erro ao cancelar assinatura' });
        }
        
        console.log(`Assinatura ${subscriptionData.id} cancelada`);
        break;
      }
      
      case 'SUBSCRIPTION_CANCELLED': {
        // Cancelar assinatura
        const { error: updateError } = await supabase
          .from('subscriptions')
          .update({ 
            status: 'canceled',
            end_date: new Date().toISOString(),
            updated_at: new Date().toISOString() 
          })
          .eq('id', subscriptionData.id);
        
        if (updateError) {
          console.error('Erro ao cancelar assinatura:', updateError);
          return res.status(500).json({ error: 'Erro ao cancelar assinatura' });
        }
        
        console.log(`Assinatura ${subscriptionData.id} cancelada`);
        break;
      }
      
      default:
        console.log(`Evento não processado: ${eventType}`);
    }
    
    return res.status(200).json({ 
      success: true, 
      message: `Evento ${eventType} processado com sucesso` 
    });
  } catch (error) {
    console.error('Erro ao processar webhook do Asaas:', error);
    return res.status(500).json({ error: 'Erro interno do servidor' });
  }
}; 