#!/usr/bin/env pwsh
# run.ps1 — Calculadora de Emissões (Django)
# Usage:
#   .\run.ps1             → setup (if needed) + start dev server
#   .\run.ps1 test        → run pytest suite
#   .\run.ps1 setup       → install/update deps + migrate only
#   .\run.ps1 check       → django system check
#   .\run.ps1 shell       → django interactive shell

param(
    [string]$Command = "server"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$AppDir  = Join-Path $PSScriptRoot "django_app"
$VenvDir = Join-Path $AppDir ".venv"
$Python  = Join-Path $VenvDir "Scripts\python.exe"
$Pip     = Join-Path $VenvDir "Scripts\pip.exe"
$Manage  = Join-Path $AppDir "manage.py"
$Reqs    = Join-Path $AppDir "requirements_django.txt"

# ── helpers ──────────────────────────────────────────────────────────────────
function Write-Step { param($msg) Write-Host "`n▶  $msg" -ForegroundColor Cyan }
function Write-Ok   { param($msg) Write-Host "   ✓ $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "   ! $msg" -ForegroundColor Yellow }

# ── 1. create venv if missing ─────────────────────────────────────────────────
if (-not (Test-Path $Python)) {
    Write-Step "Criando ambiente virtual em django_app\.venv"
    python -m venv $VenvDir
    Write-Ok "Ambiente virtual criado"
}

# ── 2. install / sync dependencies ───────────────────────────────────────────
$stamp  = Join-Path $VenvDir ".installed_stamp"
$reqsTs = (Get-Item $Reqs).LastWriteTime

if (-not (Test-Path $stamp) -or (Get-Item $stamp).LastWriteTime -lt $reqsTs) {
    Write-Step "Instalando dependências (requirements_django.txt)"
    & $Pip install --quiet --upgrade pip
    & $Pip install --quiet -r $Reqs
    Get-Date | Out-File $stamp -Encoding utf8
    Write-Ok "Dependências instaladas"
} else {
    Write-Ok "Dependências já atualizadas"
}

# ── 3. apply migrations ───────────────────────────────────────────────────────
Write-Step "Verificando migrações"
$pending = & $Python $Manage showmigrations --plan 2>&1 | Select-String "\[ \]"
if ($pending) {
    Write-Warn "Aplicando migrações pendentes"
    & $Python $Manage migrate --run-syncdb
    Write-Ok "Migrações aplicadas"
} else {
    Write-Ok "Banco de dados atualizado"
}

# ── 4. dispatch command ───────────────────────────────────────────────────────
switch ($Command.ToLower()) {

    "server" {
        Write-Step "Iniciando servidor de desenvolvimento"
        Write-Host "   Acesse: http://127.0.0.1:8000/" -ForegroundColor White
        Write-Host "   Admin:  http://127.0.0.1:8000/admin/`n" -ForegroundColor White
        & $Python $Manage runserver
    }

    "test" {
        Write-Step "Executando testes (pytest)"
        $Pytest = Join-Path $VenvDir "Scripts\pytest.exe"
        Push-Location $AppDir
        try {
            & $Pytest --tb=short -v @args
        } finally {
            Pop-Location
        }
    }

    "setup" {
        Write-Ok "Setup concluído — pronto para rodar com .\run.ps1"
    }

    "check" {
        Write-Step "Django system check"
        & $Python $Manage check
    }

    "shell" {
        Write-Step "Django shell"
        & $Python $Manage shell
    }

    "superuser" {
        Write-Step "Criar superusuário"
        & $Python $Manage createsuperuser
    }

    default {
        Write-Host "Comandos disponíveis:" -ForegroundColor Yellow
        Write-Host "  .\run.ps1              → start dev server"
        Write-Host "  .\run.ps1 test         → run pytest"
        Write-Host "  .\run.ps1 setup        → install deps + migrate"
        Write-Host "  .\run.ps1 check        → django system check"
        Write-Host "  .\run.ps1 shell        → django shell"
        Write-Host "  .\run.ps1 superuser    → create superuser"
    }
}
