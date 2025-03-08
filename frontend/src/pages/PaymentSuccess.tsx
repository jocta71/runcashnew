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

  useEffect(() => {
    // Verificar e atualizar a assinatura localmente
    const verifySubscription = async () => {
      if (sessionId) {
        try {
          // Recarregar os dados da assinatura do usuário
          await loadUserSubscription();
          
          toast({
            title: "Assinatura ativada com sucesso!",
            description: "Seu plano foi atualizado e você já pode acessar todos os recursos.",
          });
        } catch (error) {
          console.error('Erro ao verificar assinatura:', error);
        }
      }
    };

    verifySubscription();
    
    // Redirecionar após alguns segundos
    const timer = setTimeout(() => {
      navigate('/');
    }, 5000);
    
    return () => clearTimeout(timer);
  }, [sessionId, navigate, toast, loadUserSubscription]);

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
          <p className="text-gray-400 text-sm">ID da transação: {sessionId?.substring(0, 12)}...</p>
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