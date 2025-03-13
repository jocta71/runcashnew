# Script para iniciar o scraper de roletas com dados reais para MongoDB
Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "      INICIANDO SCRAPER MELHORADO      " -ForegroundColor Cyan
Write-Host "=======================================" -ForegroundColor Cyan

# Definir variáveis de ambiente
$env:MONGODB_URI = "mongodb://localhost:27017/runcash"
$env:MONGODB_DB_NAME = "runcash"

Write-Host "Configurações:" -ForegroundColor Yellow
Write-Host "* MongoDB URI: $env:MONGODB_URI" -ForegroundColor Yellow
Write-Host "* MongoDB Database: $env:MONGODB_DB_NAME" -ForegroundColor Yellow

# Função para verificar se o MongoDB está acessível
function Test-MongoDB {
    try {
        $result = python -c "import pymongo; client=pymongo.MongoClient('$env:MONGODB_URI', serverSelectionTimeoutMS=2000); client.server_info(); print('MongoDB conectado')"
        if ($result -like "*MongoDB conectado*") {
            return $true
        }
        return $false
    }
    catch {
        return $false
    }
}

# Verificar se o MongoDB está rodando
Write-Host "Verificando conexão com MongoDB..." -ForegroundColor Yellow
if (-not (Test-MongoDB)) {
    Write-Host "ERRO: Não foi possível conectar ao MongoDB. Verifique se o serviço está em execução." -ForegroundColor Red
    Write-Host "O scraper não será iniciado." -ForegroundColor Red
    exit 1
}
Write-Host "Conexão com MongoDB estabelecida com sucesso!" -ForegroundColor Green

# Número máximo de reinicializações automáticas
$maxRetries = 5
$retryCount = 0
$lastCrashTime = Get-Date

while ($retryCount -lt $maxRetries) {
    $currentTime = Get-Date
    $timeSinceLastCrash = ($currentTime - $lastCrashTime).TotalMinutes
    
    # Se a última queda foi há mais de 30 minutos, reiniciar a contagem
    if ($timeSinceLastCrash -gt 30) {
        Write-Host "Reiniciando contagem de tentativas (última queda foi há $([math]::Round($timeSinceLastCrash, 1)) minutos)" -ForegroundColor Yellow
        $retryCount = 0
    }
    
    if ($retryCount -gt 0) {
        Write-Host "Reiniciando scraper (tentativa $retryCount de $maxRetries)..." -ForegroundColor Yellow
        # Esperar um tempo maior entre as tentativas subsequentes
        $sleepTime = [math]::Min(60, 10 * $retryCount)
        Write-Host "Aguardando $sleepTime segundos antes de tentar novamente..." -ForegroundColor Yellow
        Start-Sleep -Seconds $sleepTime
    }
    
    $retryCount++
    $lastCrashTime = Get-Date
    
    Write-Host "Iniciando scraper..." -ForegroundColor Green
    try {
        # Executar o scraper em modo de dados reais
        python run_simplificado.py --mongodb
    }
    catch {
        Write-Host "Erro ao executar o scraper: $_" -ForegroundColor Red
    }
    
    Write-Host "O scraper foi encerrado ou falhou. Verificando status do MongoDB..." -ForegroundColor Yellow
    if (-not (Test-MongoDB)) {
        Write-Host "ALERTA: Conexão com MongoDB perdida!" -ForegroundColor Red
        # Aguardar até que o MongoDB esteja disponível novamente
        $mongoRetries = 0
        while (-not (Test-MongoDB) -and $mongoRetries -lt 10) {
            $mongoRetries++
            Write-Host "Tentando reconectar ao MongoDB (tentativa $mongoRetries de 10)..." -ForegroundColor Yellow
            Start-Sleep -Seconds 30
        }
        
        if (-not (Test-MongoDB)) {
            Write-Host "ERRO CRÍTICO: Não foi possível reconectar ao MongoDB após várias tentativas." -ForegroundColor Red
            Write-Host "O scraper não será reiniciado automaticamente." -ForegroundColor Red
            break
        }
        
        Write-Host "Conexão com MongoDB restabelecida!" -ForegroundColor Green
    }
}

if ($retryCount -ge $maxRetries) {
    Write-Host "ERRO: O scraper falhou $maxRetries vezes consecutivas em um curto período." -ForegroundColor Red
    Write-Host "Verifique os logs para mais informações e reinicie manualmente quando o problema for resolvido." -ForegroundColor Red
} else {
    Write-Host "O scraper foi encerrado." -ForegroundColor Cyan
}

Write-Host "Pressione qualquer tecla para fechar esta janela..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown") 