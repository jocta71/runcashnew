FROM node:18-alpine

WORKDIR /app

# Copiamos primeiro os arquivos do diretório api
COPY api/package*.json ./

RUN npm install --production

COPY api/ ./

ENV PORT=3000

EXPOSE 3000

CMD ["node", "index.js"] 