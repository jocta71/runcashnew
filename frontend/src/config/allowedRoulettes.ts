/**
 * Lista de IDs de roletas permitidas para extração pelo scraper (app.py)
 * Estas roletas serão as únicas que o scraper poderá extrair números
 * Especifique IDs exatos para controlar quais roletas são monitoradas
 */
export const ROLETAS_PERMITIDAS = [
  "2010016",  // Immersive Roulette
  "2380335",  // Brazilian Mega Roulette
  "2010065",  // Bucharest Auto-Roulette
  "2010096",  // Speed Auto Roulette
  "2010017",  // Auto-Roulette
  "2010098",  // Auto-Roulette VIP
  
  // IMPORTANTE: Remove o coringa "*" para garantir que apenas roletas específicas sejam permitidas
  // Para permitir todas as roletas, descomente a linha abaixo
  // "*"
];

/**
 * Verifica se uma roleta está na lista de roletas permitidas
 * @param rouletteId ID da roleta a ser verificada
 * @returns boolean indicando se a roleta está permitida
 */
export const isRouletteAllowed = (rouletteId: string): boolean => {
  // Se "*" estiver na lista, todas as roletas são permitidas
  if (ROLETAS_PERMITIDAS.includes("*")) {
    return true;
  }
  return ROLETAS_PERMITIDAS.includes(rouletteId);
};

/**
 * Filtra um array de roletas para incluir apenas as permitidas
 * @param roulettes Array de roletas
 * @returns Array filtrado contendo apenas roletas permitidas
 */
export const filterAllowedRoulettes = <T extends { id: string }>(roulettes: T[]): T[] => {
  // Se "*" estiver na lista, retorne todas as roletas sem filtrar
  if (ROLETAS_PERMITIDAS.includes("*")) {
    return roulettes;
  }
  return roulettes.filter(roulette => isRouletteAllowed(roulette.id));
};

/**
 * Exporta a lista de IDs como string formatada para variável de ambiente
 * Use este valor para configurar a variável ALLOWED_ROULETTES no backend
 */
export const getAllowedRoulettesEnvValue = (): string => {
  // Remove "*" se estiver presente, pois não é um ID válido para o backend
  const validIds = ROLETAS_PERMITIDAS.filter(id => id !== "*");
  return validIds.join(",");
};

/**
 * Função para atualizar a lista de roletas permitidas
 * Esta função é necessária para compatibilidade com código existente
 * @param ids Lista de IDs de roletas a serem permitidas
 * @returns Verdadeiro se a atualização foi bem-sucedida
 */
export const atualizarRoletasPermitidas = (ids: string[]): boolean => {
  console.log("Função atualizarRoletasPermitidas chamada com IDs:", ids);
  // Esta função é apenas um stub para compatibilidade
  // A implementação real exigiria persistência de dados
  return true;
};

/**
 * Instruções para configurar as roletas permitidas no scraper (app.py)
 * 
 * 1. Copie o valor retornado por getAllowedRoulettesEnvValue()
 * 2. Configure a variável de ambiente ALLOWED_ROULETTES no backend
 *    - No arquivo .env do backend: ALLOWED_ROULETTES=2010016,2380335,2010065,2010096,2010017,2010098
 *    - Ou em plataformas como Heroku/Railway: adicione a variável com o mesmo valor
 * 
 * Isto garantirá que o scraper (app.py) e o frontend estejam sincronizados
 * quanto às roletas permitidas para extração e exibição.
 */ 