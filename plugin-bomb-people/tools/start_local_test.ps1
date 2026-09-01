[CmdletBinding()]
param(
    [ValidateRange(1024, 65535)]
    [int]$WebPort = 4173,
    [ValidateRange(1024, 65535)]
    [int]$ApiPort = 10619,
    [switch]$NoOpen
)

$ErrorActionPreference = 'Stop'
$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$hallRoot = (Resolve-Path (Join-Path $pluginRoot '..\..')).Path
$serverScript = Join-Path $pluginRoot 'tools\local_test_server.py'
$viteCommand = Join-Path $hallRoot 'frontend\node_modules\.bin\vite.cmd'
$viteConfig = Join-Path $pluginRoot 'dev\vite.config.mjs'
$logRoot = Join-Path $pluginRoot '.local-test'
$serverOut = Join-Path $logRoot 'server.out.log'
$serverError = Join-Path $logRoot 'server.error.log'

if (-not (Test-Path -LiteralPath $viteCommand -PathType Leaf)) {
    throw '缺少前端依赖。请先在游戏大厅 frontend 目录执行 npm install。'
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw '找不到 Python。请先安装 Python 并加入 PATH。'
}

New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$pythonCommand = (Get-Command python).Source
$serverProcess = $null
$previousApiPort = $env:BOMB_PEOPLE_API_PORT

try {
    $serverProcess = Start-Process `
        -FilePath $pythonCommand `
        -ArgumentList @($serverScript, '--port', $ApiPort) `
        -WorkingDirectory $hallRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $serverOut `
        -RedirectStandardError $serverError `
        -PassThru

    $healthy = $false
    for ($attempt = 0; $attempt -lt 40; $attempt += 1) {
        if ($serverProcess.HasExited) { break }
        try {
            $response = Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 -Uri "http://127.0.0.1:$ApiPort/api/health"
            if ($response.StatusCode -eq 200) {
                $healthy = $true
                break
            }
        } catch {
            Start-Sleep -Milliseconds 125
        }
    }
    if (-not $healthy) {
        $details = if (Test-Path -LiteralPath $serverError) { Get-Content -Raw -LiteralPath $serverError } else { '' }
        throw "本地规则服务启动失败。$details"
    }

    $env:BOMB_PEOPLE_API_PORT = "$ApiPort"
    Write-Host "炸弹超人本地测试台：http://127.0.0.1:$WebPort" -ForegroundColor Cyan
    Write-Host '按 Ctrl+C 可同时停止前端与本地规则服务。' -ForegroundColor DarkGray
    $viteArguments = @('--config', $viteConfig, '--host', '127.0.0.1', '--port', $WebPort, '--strictPort')
    if (-not $NoOpen) { $viteArguments += '--open' }
    & $viteCommand @viteArguments
} finally {
    $env:BOMB_PEOPLE_API_PORT = $previousApiPort
    if ($serverProcess -and -not $serverProcess.HasExited) {
        Stop-Process -Id $serverProcess.Id -Force
        $serverProcess.WaitForExit()
    }
}
