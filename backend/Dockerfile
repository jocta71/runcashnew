FROM python:3.11-slim

WORKDIR /app

# Instalar Google Chrome e suas dependências
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    gnupg \
    libgconf-2-4 \
    libgtk-3-0 \
    libxss1 \
    libnss3 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Instalar Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar variáveis de ambiente para o Chrome
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_PATH=/usr/lib/google-chrome

# Copiar arquivos de requisitos e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install gunicorn

# Copiar o código da aplicação
COPY . .

# Porta para o servidor Flask
EXPOSE 8080

# Comando para rodar a aplicação com Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "scraper.app:app", "--timeout", "0", "--workers", "1", "--threads", "2"] 