import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useToast } from '@/hooks/use-toast';
import { useSubscription } from '@/context/SubscriptionContext';
import { Loader2 } from 'lucide-react';

const PaymentSuccess = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { toast } = useToast();
  const { loadUserSubscription } = useSubscription();
  const sessionId = searchParams.get('session_id');
  const isFree = searchParams.get('free') === 'true';
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    console.log('PaymentSuccess - Renderizando com sessionId:', sessionId, 'isFree:', isFree);
    
    // Verificar e atualizar a assinatura localmente
    const verifySubscription = async () => {
      console.log('Iniciando verificação de assinatura');
      setLoading(true);
      
      try {
        // Timeout para limitar o tempo de espera da operação
        const timeoutPromise = new Promise((_, reject) => 
          setTimeout(() => reject(new Error('Tempo limite excedido')), 10000)
        );
        
        // Recarregar os dados da assinatura do usuário
        console.log('Carregando dados de assinatura do usuário');
        await Promise.race([
          loadUserSubscription(),
          timeoutPromise
        ]);
        
        // Sempre mostrar o toast de sucesso, seja plano gratuito ou pago
        toast({
          title: "Assinatura ativada com sucesso!",
          description: "Seu plano foi atualizado e você já pode acessar todos os recursos.",
        });
        
        console.log('Assinatura carregada e toast exibido');
        setLoading(false);
      } catch (error) {
        console.error('Erro ao verificar assinatura:', error);
        
        // Verificar se é um erro de timeout ou outro problema
        if (error instanceof Error && error.message === 'Tempo limite excedido') {
          setError('O processo está demorando mais que o esperado. Sua assinatura será ativada em breve.');
        } else {
          setError('Não foi possível verificar sua assinatura. Ela será atualizada em instantes.');
        }
        
        // Mesmo com erro, mostrar mensagem de sucesso para o usuário
        toast({
          title: "Assinatura recebida!",
          description: "Seu plano será ativado em breve.",
        });
        
        setLoading(false);
      }
    };

    // Iniciar a verificação
    verifySubscription();
    
    // Redirecionar após alguns segundos
    console.log('Configurando timer para redirecionamento');
    const timer = setTimeout(() => {
      console.log('Redirecionando para página inicial');
      navigate('/');
    }, 5000); // 5 segundos
    
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
          {loading ? 'Estamos processando sua assinatura...' : 'Sua assinatura foi ativada com sucesso. Agora você tem acesso a todos os recursos do seu novo plano.'}
        </p>
        
        {loading && (
          <div className="flex justify-center items-center mb-6">
            <Loader2 className="h-8 w-8 animate-spin text-vegas-gold" />
          </div>
        )}
        
        {error && (
          <div className="w-full bg-vegas-black rounded-md p-4 mb-6 border border-yellow-600">
            <p className="text-yellow-500 text-sm">{error}</p>
          </div>
        )}
        
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
          Você será redirecionado para a página inicial em instantes...
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