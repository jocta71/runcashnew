FROM node:18

WORKDIR /app

# Copiar todo o diretório api
COPY api/ ./

# Instalar dependências
RUN npm install --production

# Definir variáveis de ambiente
ENV PORT=3000

# Expor a porta
EXPOSE 3000

# Comando para iniciar a aplicação
CMD ["node", "index.js"] 