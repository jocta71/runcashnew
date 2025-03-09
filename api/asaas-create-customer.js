const axios = require('axios');

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
    const { name, email, cpfCnpj, mobilePhone } = req.body;
    
    // Validar dados
    if (!name || !email || !cpfCnpj) {
      return res.status(400).json({ error: 'Dados obrigatórios não fornecidos' });
    }

    // Chamada API do Asaas para criar cliente
    const response = await axios.post(
      'https://sandbox.asaas.com/api/v3/customers', // Usar sandbox para testes, mudar para produção depois
      {
        name,
        email,
        cpfCnpj,
        mobilePhone,
        notificationDisabled: false
      },
      {
        headers: {
          'access_token': process.env.ASAAS_API_KEY,
          'Content-Type': 'application/json'
        }
      }
    );

    console.log('Cliente criado com sucesso:', response.data);
    
    return res.status(200).json({ 
      success: true, 
      customerId: response.data.id, 
      message: 'Cliente criado com sucesso' 
    });
  } catch (error) {
    console.error('Erro ao criar cliente no Asaas:', error.response?.data || error.message);
    
    // Verificar se o cliente já existe
    if (error.response?.data?.errors?.[0]?.code === 'invalid_cpfCnpj' && 
        error.response?.data?.errors?.[0]?.description?.includes('já utilizado')) {
      // Buscar cliente pelo CPF/CNPJ
      try {
        const cpfCnpj = req.body.cpfCnpj.replace(/[^\d]+/g, '');
        const searchResponse = await axios.get(
          `https://sandbox.asaas.com/api/v3/customers?cpfCnpj=${cpfCnpj}`,
          {
            headers: {
              'access_token': process.env.ASAAS_API_KEY
            }
          }
        );
        
        if (searchResponse.data.data && searchResponse.data.data.length > 0) {
          return res.status(200).json({ 
            success: true, 
            customerId: searchResponse.data.data[0].id, 
            message: 'Cliente existente recuperado com sucesso' 
          });
        }
      } catch (searchError) {
        console.error('Erro ao buscar cliente:', searchError);
      }
    }
    
    return res.status(500).json({ 
      error: 'Erro ao criar cliente', 
      details: error.response?.data || error.message 
    });
  }
}; 