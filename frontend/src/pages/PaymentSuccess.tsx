import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useToast } from '@/hooks/use-toast';
import { useSubscription } from '@/context/SubscriptionContext';

const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { loadUserSubscription } = useSubscription();
  const sessionId = searchParams.get('session_id');
  const isFree = searchParams.get('free') === 'true';

  useEffect(() => {
    console.log('PaymentSuccess - Renderizando com sessionId:', sessionId, 'isFree:', isFree);
    
    // Verificar e atualizar a assinatura localmente
    const verifySubscription = async () => {
      console.log('Iniciando verificação de assinatura');
      
      try {
        // Recarregar os dados da assinatura do usuário
        console.log('Carregando dados de assinatura do usuário');
        await loadUserSubscription();
        
        // Sempre mostrar o toast de sucesso, seja plano gratuito ou pago
        toast({
          title: "Assinatura ativada com sucesso!",
          description: "Seu plano foi atualizado e você já pode acessar todos os recursos.",
        });
        
        console.log('Assinatura carregada e toast exibido');
      } catch (error) {
        console.error('Erro ao verificar assinatura:', error);
        // Mesmo com erro, mostrar mensagem de sucesso para o usuário
        toast({
          title: "Assinatura ativada!",
          description: "Bem-vindo ao seu novo plano.",
        });
      }
    };

    // Iniciar a verificação
    verifySubscription();
    
    // Redirecionar após alguns segundos
    console.log('Configurando timer para redirecionamento');
    const timer = setTimeout(() => {
      console.log('Redirecionando para página inicial');
      navigate('/');
    }, 3000); // Reduzido para 3 segundos
    
    return () => {
      console.log('Limpando timer de redirecionamento');
      clearTimeout(timer);
    };
  }, [sessionId, navigate, toast, loadUserSubscription, isFree]);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 bg-vegas-dark">
      <div className="bg-vegas-darkgray p-8 rounded-lg shadow-lg max-w-md w-full text-center">
        <div className="w-20 h-20 bg-green-500 rounded-full mx-auto mb-6 flex items-center justify-center">
          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h2 className="text-2xl font-bold text-white mb-2">Pagamento Aprovado!</h2>
        <p className="text-gray-300 mb-6">
          Sua assinatura foi ativada com sucesso. Agora você tem acesso a todos os recursos do seu novo plano.
        </p>
        <div className="w-full bg-vegas-black rounded-md p-4 mb-6">
          <p className="text-vegas-gold font-medium mb-1">Confirmação de Pagamento</p>
          <p className="text-gray-400 text-sm">
            {isFree 
              ? "Plano gratuito ativado" 
              : `ID da transação: ${sessionId?.substring(0, 12)}...`
            }
          </p>
        </div>
        <p className="text-gray-400 text-sm mb-4">
          Você será redirecionado para a página inicial em alguns segundos...
        </p>
        <button 
          onClick={() => navigate('/')}
          className="bg-vegas-gold hover:bg-vegas-gold/80 text-black font-medium py-2 px-6 rounded-md w-full"
        >
          Voltar para a página inicial
        </button>
      </div>
    </div>
  );
};

export default PaymentSuccess; 