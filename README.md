# RunCash

Um sistema completo para rastreamento de roletas e análise de estratégias.

## Estrutura do Projeto

O projeto foi reorganizado para uma estrutura mais clara e organizada:

- **frontend/** - Interface de usuário React
- **backend/** - API e lógica do servidor
- **api/** - Endpoints da API
- **docs/** - Toda a documentação do projeto
- **scripts/** - Scripts de utilidades, banco de dados e manutenção

Para detalhes completos sobre a reorganização, consulte [docs/reorganizacao-projeto.md](docs/reorganizacao-projeto.md).

## Principais Recursos

- Rastreamento em tempo real de números de roletas
- Análise estatística e sugestões de estratégias
- Dashboard de dados históricos
- Autenticação e gerenciamento de usuários
- Sistema de pagamento para recursos premium

## Início Rápido

### Pré-requisitos

- Node.js 16+
- Python 3.9+
- Um banco de dados Supabase

### Instalação

1. Clone o repositório:
   ```
   git clone https://github.com/jocta71/runcashnew.git
   cd runcashnew
   ```

2. Instale as dependências do frontend:
   ```
   cd frontend
   npm install
   ```

3. Instale as dependências do backend:
   ```
   cd ../backend/api
   npm install
   cd ../scraper
   pip install -r requirements.txt
   ```

4. Configure as variáveis de ambiente:
   - Copie `.env.example` para `.env` nas pastas frontend e backend
   - Preencha com suas próprias credenciais

### Executando o Projeto

1. Para executar apenas o frontend:
   ```
   npm run frontend:dev
   ```

2. Para executar apenas a API do backend:
   ```
   npm run backend:api
   ```

3. Para executar o scraper do backend:
   ```
   npm run backend:scraper
   ```

4. Para executar tudo ao mesmo tempo:
   ```
   npm start
   ```

## Estrutura de Diretórios

```
/
├── frontend/               # Interface do usuário
│   ├── api/                # APIs serverless do frontend
│   ├── src/                # Código fonte
│   └── ...
├── backend/                # Componentes do servidor
│   ├── api/                # API REST principal
│   │   ├── payment/        # APIs de processamento de pagamento
│   │   └── ...
│   ├── scraper/            # Scraper para coleta de dados
│   └── ...
├── docs/                   # Documentação
├── scripts/                # Scripts utilitários
└── ...
```

## Documentação

Consulte o diretório `docs/` para documentação detalhada:

- [Instruções de Deployment](docs/deploy-instructions.md)
- [Configuração do Stripe](docs/STRIPE_SETUP.md)
- [API Keys](docs/API_KEYS.md)

## Desenvolvimento

Para contribuir com o projeto, confira as informações em [docs/github-upload-instructions.md](docs/github-upload-instructions.md).

## Licença

Este projeto está licenciado sob a Licença MIT. 