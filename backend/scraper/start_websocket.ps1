# Script para iniciar o servidor WebSocket no Windows

Write-Host "Iniciando servidor WebSocket para comunicação em tempo real..." -ForegroundColor Green

# Verificar se Node.js está instalado
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js não encontrado. Por favor, instale o Node.js." -ForegroundColor Red
    exit 1
}

# Carregar variáveis de ambiente, se existirem
if (Test-Path .env) {
    Write-Host "Carregando variáveis de ambiente de .env..." -ForegroundColor Cyan
    Get-Content .env | ForEach-Object {
        if (-not [string]::IsNullOrWhiteSpace($_) -and -not $_.StartsWith('#')) {
            $key, $value = $_.Split('=', 2)
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

# Definir variáveis padrão
if (-not $env:PORT) { $env:PORT = "5000" }
if (-not $env:MONGODB_URI) { $env:MONGODB_URI = "mongodb://localhost:27017/runcash" }
if (-not $env:MONGODB_DB_NAME) { $env:MONGODB_DB_NAME = "runcash" }
if (-not $env:ALLOWED_ORIGINS) { $env:ALLOWED_ORIGINS = "https://runcashnew-frontend-nu.vercel.app,http://localhost:3000" }

Write-Host "Configuração:" -ForegroundColor Yellow
Write-Host "* Porta: $env:PORT" -ForegroundColor Yellow
Write-Host "* MongoDB URI: $env:MONGODB_URI" -ForegroundColor Yellow
Write-Host "* MongoDB Database: $env:MONGODB_DB_NAME" -ForegroundColor Yellow
Write-Host "* CORS Origins: $env:ALLOWED_ORIGINS" -ForegroundColor Yellow

# Verificar se o package.json existe ou criar um básico
if (-not (Test-Path package.json)) {
    Write-Host "Criando package.json..." -ForegroundColor Cyan
    @"
{
  "name": "websocket-server",
  "version": "1.0.0",
  "description": "Server WebSocket para RunCash",
  "main": "websocket_server.js",
  "dependencies": {
    "cors": "^2.8.5",
    "dotenv": "^16.0.3",
    "express": "^4.18.2",
    "mongodb": "^5.0.0",
    "socket.io": "^4.6.1"
  }
}
"@ | Out-File -FilePath package.json -Encoding utf8
}

# Instalar dependências necessárias
Write-Host "Verificando e instalando dependências..." -ForegroundColor Cyan
npm install socket.io express cors mongodb dotenv

# Executar servidor
Write-Host "Iniciando servidor WebSocket..." -ForegroundColor Green
node websocket_server.js 