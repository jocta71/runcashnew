# Script para inserir dados de exemplo no MongoDB
Write-Host "Iniciando script para inserir dados de exemplo no MongoDB..." -ForegroundColor Cyan

# Verificar se o Node.js está instalado
$nodeVersion = node --version
if (-not $?) {
    Write-Host "Erro: Node.js não está instalado. Por favor, instale o Node.js para continuar." -ForegroundColor Red
    exit 1
}

Write-Host "Node.js $nodeVersion encontrado." -ForegroundColor Green

# Verificar se o servidor WebSocket está em execução
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5000/api/status" -Method GET -TimeoutSec 5
    if ($response.StatusCode -eq 200) {
        Write-Host "Servidor WebSocket está em execução. Pronto para inserir dados." -ForegroundColor Green
    } else {
        Write-Host "Servidor WebSocket respondeu com status inesperado: $($response.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "Erro ao verificar o servidor WebSocket. Certifique-se de que ele está em execução." -ForegroundColor Red
    Write-Host "Erro: $_" -ForegroundColor Red
    
    $startServer = Read-Host "Deseja iniciar o servidor WebSocket agora? (S/N)"
    if ($startServer -eq "S" -or $startServer -eq "s") {
        Write-Host "Iniciando servidor WebSocket..." -ForegroundColor Yellow
        Start-Process powershell -ArgumentList "-NoExit", "-File", ".\start_websocket.ps1"
        Write-Host "Aguardando o servidor iniciar (15 segundos)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 15
    } else {
        Write-Host "Sem servidor WebSocket, não é possível continuar." -ForegroundColor Red
        exit 1
    }
}

# Executar o script para inserir dados
Write-Host "Iniciando inserção de dados de exemplo..." -ForegroundColor Cyan
node insert_sample_data.js

if ($LASTEXITCODE -eq 0) {
    Write-Host "Dados de exemplo inseridos com sucesso!" -ForegroundColor Green
} else {
    Write-Host "Erro ao inserir dados de exemplo. Código de saída: $LASTEXITCODE" -ForegroundColor Red
}

# Pausar para que o usuário possa ver os resultados
Write-Host ""
Write-Host "Pressione qualquer tecla para continuar..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 