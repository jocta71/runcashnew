import React, { memo, useEffect, useState } from 'react';
import Lottie from 'lottie-react';

interface RouletteAnimationProps {
  state: string;
  className?: string;
}

const animationUrls = {
  WIN: "https://lottie.host/2769b6e7-cd37-4b14-ace0-88b6a7937a77/ejXIAryeqn.json",
  LOSS: "https://lottie.host/2769b6e7-cd37-4b14-ace0-88b6a7937a77/ejXIAryeqn.json",
  NEUTRAL: "https://lottie.host/1c1847c8-283f-45bd-854c-536eb07810d2/fqsf5HKLMV.json",
  GALE: "https://lottie.host/d12eea72-9dde-4ef1-8b61-e51264a3f66a/RLLg7zgwVp.json",
  TRIGGER: "https://lottie.host/1ca4b9a2-fdc3-475f-92f5-1af4abd7d58b/S3i9mjuf7q.json",
  MORTO: "https://lottie.host/1c1847c8-283f-45bd-854c-536eb07810d2/fqsf5HKLMV.json",
  POST_GALE_NEUTRAL: "https://lottie.host/d12eea72-9dde-4ef1-8b61-e51264a3f66a/RLLg7zgwVp.json"
};

const RouletteAnimation = memo(({ state, className = '' }: RouletteAnimationProps) => {
  const [animationData, setAnimationData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Determinar a URL da animação com base no estado
    const url = animationUrls[state as keyof typeof animationUrls] || animationUrls.NEUTRAL;
    
    // Buscar os dados da animação
    const fetchAnimationData = async () => {
      try {
        setIsLoading(true);
        const response = await fetch(url);
        const data = await response.json();
        setAnimationData(data);
        setIsLoading(false);
      } catch (error) {
        console.error("Erro ao carregar a animação:", error);
        setIsLoading(false);
      }
    };

    fetchAnimationData();
  }, [state]);

  if (isLoading || !animationData) {
    return null; // Ou um spinner/loading
  }

  return (
    <div className={`absolute top-0 right-0 w-24 h-24 pointer-events-none ${className}`}>
      <Lottie
        animationData={animationData}
        loop={true}
        autoplay={true}
        style={{ width: '100%', height: '100%' }}
      />
    </div>
  );
});

RouletteAnimation.displayName = 'RouletteAnimation';

export default RouletteAnimation; 