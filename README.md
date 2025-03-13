# RunCash - Sistema de Análise de Roletas

## Sistema de Dados Reais

O sistema RunCash foi atualizado para utilizar apenas dados reais do MongoDB:

- Exibe apenas dados reais do MongoDB na página principal
- Mostra mensagem "Sem Dados Disponíveis" quando não há números no banco
- Conecta-se via WebSocket para atualizações em tempo real

## Configuração e Uso

### Pré-requisitos

- Node.js (v16 ou superior)
- MongoDB instalado e em execução (na porta padrão 27017)
- Git (opcional, para clonar o repositório)

### Passos para Execução

1. **Iniciar o Servidor WebSocket** (conecta ao MongoDB):
   ```
   cd backend
   .\start_websocket.ps1
   ```
   Isso iniciará o servidor WebSocket na porta 5000, que conectará ao MongoDB e servirá os dados em tempo real.

2. **Iniciar o Frontend**:
   ```
   cd frontend
   npm install
   npm run dev
   ```
   Isso iniciará o servidor de desenvolvimento do frontend.

3. **Acessar o Sistema**:
   ```
   http://localhost:5173/
   ```

### Populando o Banco de Dados

Se não houver dados no MongoDB, você precisará inserir alguns números:

1. **Usar o Script de Exemplo**:
   ```
   cd backend
   .\insert_data.ps1
   ```
   Isso insere dados de exemplo para todas as roletas disponíveis.

2. **Inserir Números Manualmente**:
   ```
   cd backend
   node test_insert_number.js "Lightning Roulette" 17
   ```
   Isso insere o número 17 para a roleta "Lightning Roulette".

## Solução de Problemas

Se você não estiver vendo nenhum número na página, verifique os seguintes itens:

1. Verifique se o servidor WebSocket está em execução (deve mostrar "Conectado em tempo real" no topo da página)
2. Execute o script `.\insert_data.ps1` para inserir dados de exemplo
3. Recarregue a página para ver os novos dados

## Desenvolvimento

### Estrutura de Arquivos

- `frontend/`: Aplicação React 
  - `src/pages/Index.tsx`: Página principal (dados reais do MongoDB)
  
- `backend/`: Servidor WebSocket e API
  - `websocket_server.js`: Servidor que conecta ao MongoDB
  - `insert_sample_data.js`: Script para inserir dados de exemplo
  - `test_insert_number.js`: Script para inserir um número específico

### Criando Novas Roletas

Para adicionar uma nova roleta, insira um número para ela no MongoDB e ela aparecerá automaticamente na página principal.

## Licença

Este projeto está licenciado sob a licença MIT. 