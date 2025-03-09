import { useState, useEffect } from 'react';
import { getAllowedRoulettesEnvValue, ROLETAS_PERMITIDAS } from '@/config/allowedRoulettes';
import { supabase } from '@/integrations/supabase/client';
import { fetchAllRoulettes } from '@/integrations/api/rouletteService';

/**
 * Página para sincronizar configurações entre frontend e backend
 * Mostra as roletas permitidas e gera o valor para a variável de ambiente ALLOWED_ROULETTES
 */
const ConfigSync = () => {
  const [allRoulettes, setAllRoulettes] = useState<Array<{id: string; nome: string}>>([]);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  
  const envValue = getAllowedRoulettesEnvValue();
  
  useEffect(() => {
    const loadRoulettes = async () => {
      try {
        setLoading(true);
        const roulettes = await fetchAllRoulettes();
        setAllRoulettes(roulettes.map(r => ({id: r.id, nome: r.nome})));
      } catch (error) {
        console.error("Erro ao carregar roletas:", error);
      } finally {
        setLoading(false);
      }
    };
    
    loadRoulettes();
  }, []);
  
  const copyToClipboard = () => {
    navigator.clipboard.writeText(envValue);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  return (
    <div className="p-8 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Configuração de Roletas Permitidas</h1>
      
      <div className="bg-black/20 p-6 rounded-lg mb-8">
        <h2 className="text-xl font-semibold mb-4">Variável de Ambiente para o Backend</h2>
        <p className="mb-4">Copie este valor para a variável <code className="bg-black/30 px-2 py-1 rounded">ALLOWED_ROULETTES</code> no arquivo .env do backend:</p>
        
        <div className="flex items-center mb-4">
          <code className="bg-black/30 p-3 rounded flex-1 overflow-x-auto">{envValue}</code>
          <button 
            onClick={copyToClipboard}
            className="ml-4 bg-[#00ff00] text-black px-4 py-2 rounded hover:bg-[#00dd00] transition-colors"
          >
            {copied ? 'Copiado!' : 'Copiar'}
          </button>
        </div>
        
        <p className="text-sm text-gray-400">
          Esta configuração garante que o scraper (app.py) extraia dados apenas das roletas permitidas.
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">Roletas Permitidas ({ROLETAS_PERMITIDAS.length})</h2>
          {loading ? (
            <div className="animate-pulse bg-white/10 h-40 rounded-lg"></div>
          ) : (
            <div className="bg-black/20 p-4 rounded-lg h-[400px] overflow-y-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="text-left p-2">ID</th>
                    <th className="text-left p-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {ROLETAS_PERMITIDAS.map(id => {
                    const found = allRoulettes.find(r => r.id === id);
                    return (
                      <tr key={id} className="border-t border-white/10">
                        <td className="p-2">{id}</td>
                        <td className="p-2">
                          {found ? (
                            <span className="text-green-400 flex items-center">
                              <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                              {found.nome}
                            </span>
                          ) : (
                            <span className="text-yellow-400 flex items-center">
                              <span className="w-2 h-2 bg-yellow-400 rounded-full mr-2"></span>
                              Não encontrada
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
        
        <div>
          <h2 className="text-xl font-semibold mb-4">Todas as Roletas ({allRoulettes.length})</h2>
          {loading ? (
            <div className="animate-pulse bg-white/10 h-40 rounded-lg"></div>
          ) : (
            <div className="bg-black/20 p-4 rounded-lg h-[400px] overflow-y-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="text-left p-2">Nome</th>
                    <th className="text-left p-2">ID</th>
                    <th className="text-left p-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {allRoulettes.map(roulette => {
                    const isAllowed = ROLETAS_PERMITIDAS.includes(roulette.id);
                    return (
                      <tr key={roulette.id} className="border-t border-white/10">
                        <td className="p-2">{roulette.nome}</td>
                        <td className="p-2 text-xs opacity-70">{roulette.id}</td>
                        <td className="p-2">
                          {isAllowed ? (
                            <span className="text-green-400 flex items-center">
                              <span className="w-2 h-2 bg-green-400 rounded-full mr-2"></span>
                              Permitida
                            </span>
                          ) : (
                            <span className="text-red-400 flex items-center">
                              <span className="w-2 h-2 bg-red-400 rounded-full mr-2"></span>
                              Bloqueada
                            </span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
      
      <div className="bg-black/20 p-6 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">Instruções</h2>
        <ol className="list-decimal pl-5 space-y-2">
          <li>Edite a lista de roletas permitidas no arquivo <code>allowedRoulettes.ts</code>.</li>
          <li>Copie o valor da variável de ambiente gerado acima.</li>
          <li>Adicione esse valor à variável <code>ALLOWED_ROULETTES</code> no arquivo <code>.env</code> do backend.</li>
          <li>Reinicie o scraper (app.py) para que ele reconheça as novas configurações.</li>
        </ol>
      </div>
    </div>
  );
};

export default ConfigSync; 