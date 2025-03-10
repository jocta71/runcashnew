import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import NotFound from "./pages/NotFound";
import AuthPage from "./pages/AuthPage";
import PaymentSuccess from "./pages/PaymentSuccess";
import PaymentCanceled from "./pages/PaymentCanceled";
import PlansPage from "./pages/PlansPage";
import ProfilePage from "./pages/ProfilePage";
import SeedPage from "./pages/SeedPage";
import { AuthProvider } from "./context/AuthContext";
import { SubscriptionProvider } from "./context/SubscriptionContext";
import ProtectedRoute from "./components/ProtectedRoute";
import AuthRoute from "./components/AuthRoute";
import { useEffect } from "react";

const queryClient = new QueryClient();

// Componente específico para desativar o comportamento de recarregar
const PreventReload = () => {
  useEffect(() => {
    // Função para prevenir recarregamento quando a aba volta ao foco
    const handleVisibilityChange = () => {
      // Evita que a página recarregue quando volta a ter foco
      if (document.visibilityState === 'visible') {
        // Cancelamos qualquer comportamento padrão que possa estar causando o reload
        window.stop();
      }
    };

    // Adiciona o listener para mudanças de visibilidade
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // Função para prevenir refresh ao voltar para a página via histórico
    window.addEventListener('pageshow', (event) => {
      if (event.persisted) {
        // Se a página foi carregada do cache (voltar/avançar do navegador)
        window.stop();
      }
    });

    // Limpa os listeners quando o componente é desmontado
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('pageshow', null);
    };
  }, []);

  return null;
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <SubscriptionProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <PreventReload />
          <BrowserRouter>
            <Routes>
              {/* Rota pública - apenas para não-autenticados */}
              <Route path="/auth" element={
                <AuthRoute>
                  <AuthPage />
                </AuthRoute>
              } />
              
              {/* Página para popular números das roletas */}
              <Route path="/seed-numbers" element={<SeedPage />} />
              
              {/* Rotas protegidas - apenas para usuários autenticados */}
              <Route path="/" element={
                <ProtectedRoute>
                  <Index />
                </ProtectedRoute>
              } />
              
              {/* Rotas relacionadas a planos e pagamentos */}
              <Route path="/planos" element={
                <ProtectedRoute>
                  <PlansPage />
                </ProtectedRoute>
              } />
              
              <Route path="/payment-success" element={
                <ProtectedRoute>
                  <PaymentSuccess />
                </ProtectedRoute>
              } />
              
              <Route path="/payment-canceled" element={
                <ProtectedRoute>
                  <PaymentCanceled />
                </ProtectedRoute>
              } />
              
              {/* Rota de perfil do usuário */}
              <Route path="/profile" element={
                <ProtectedRoute>
                  <ProfilePage />
                </ProtectedRoute>
              } />
              
              {/* Rota para página não encontrada - também protegida */}
              <Route path="*" element={
                <ProtectedRoute>
                  <NotFound />
                </ProtectedRoute>
              } />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </SubscriptionProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
