param (
    [string]$Mode = "all"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Asegurar variables de entorno y paths
$env:Path = "$ScriptDir\.venv\Scripts;$env:USERPROFILE\.local\bin;$env:Path"
$env:PYTHONPATH = "$ScriptDir\src"

function Start-AgentServer {
    Write-Host "[1/2] Iniciando Agente Python (FastAPI en puerto 8000)..." -ForegroundColor Cyan
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir'; `$env:PYTHONPATH = '$ScriptDir\src'; & '$ScriptDir\.venv\Scripts\python.exe' -m agente.main"
}

function Start-WhatsAppBridge {
    Write-Host "[2/2] Iniciando WhatsApp Bridge (Node.js en puerto 3000)..." -ForegroundColor Green
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$ScriptDir\bridge'; node index.js"
}

function Start-CLI {
    Write-Host "Iniciando Agente en modo interactivo CLI..." -ForegroundColor Yellow
    cd $ScriptDir
    $env:PYTHONPATH = "$ScriptDir\src"
    & "$ScriptDir\.venv\Scripts\python.exe" -m agente.main --cli
}

switch ($Mode.ToLower()) {
    "cli" {
        Start-CLI
    }
    "agent" {
        cd $ScriptDir
        $env:PYTHONPATH = "$ScriptDir\src"
        & "$ScriptDir\.venv\Scripts\python.exe" -m agente.main
    }
    "bridge" {
        cd "$ScriptDir\bridge"
        node index.js
    }
    "all" {
        Write-Host "=================================================" -ForegroundColor Magenta
        Write-Host "🚀 Iniciando Agente de IA para Tareas Diarias" -ForegroundColor Magenta
        Write-Host "=================================================" -ForegroundColor Magenta
        Start-AgentServer
        Start-Sleep -Seconds 2
        Start-WhatsAppBridge
        Write-Host ""
        Write-Host "Ambos servicios se han iniciado en ventanas independientes." -ForegroundColor White
        Write-Host "1. Abre tu navegador en http://localhost:3000/qr para escanear el QR con WhatsApp." -ForegroundColor Cyan
        Write-Host "2. Tu agente responderá automáticamente a tus mensajes." -ForegroundColor Green
    }
    default {
        Write-Host "Modo no reconocido: $Mode. Opciones: all, cli, agent, bridge." -ForegroundColor Red
    }
}
