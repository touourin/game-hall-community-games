[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$pluginRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$hallRoot = (Resolve-Path (Join-Path $pluginRoot '..\..')).Path
$vueTsc = Join-Path $hallRoot 'frontend\node_modules\.bin\vue-tsc.cmd'
$vitest = Join-Path $hallRoot 'frontend\node_modules\.bin\vitest.cmd'
$vite = Join-Path $hallRoot 'frontend\node_modules\.bin\vite.cmd'
$viteConfig = Join-Path $pluginRoot 'dev\vite.config.mjs'

foreach ($command in @($vueTsc, $vitest, $vite)) {
    if (-not (Test-Path -LiteralPath $command -PathType Leaf)) {
        throw '缺少前端依赖。请先在游戏大厅 frontend 目录执行 npm install。'
    }
}
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw '找不到 Python。请先安装 Python 并加入 PATH。'
}

Push-Location $hallRoot
try {
    Write-Host '1/5 后端规则与本地测试服务测试' -ForegroundColor Cyan
    python -m pytest "$pluginRoot\tests" -q
    if ($LASTEXITCODE -ne 0) { throw '后端测试失败' }

    Write-Host '2/5 正式插件 TypeScript 类型检查' -ForegroundColor Cyan
    & $vueTsc -p "$pluginRoot\tsconfig.json" --noEmit
    if ($LASTEXITCODE -ne 0) { throw 'TypeScript 类型检查失败' }

    Write-Host '3/5 本地测试台 TypeScript 类型检查' -ForegroundColor Cyan
    & $vueTsc -p "$pluginRoot\dev\tsconfig.json" --noEmit
    if ($LASTEXITCODE -ne 0) { throw '本地测试台类型检查失败' }

    Write-Host '4/5 游戏界面组件测试' -ForegroundColor Cyan
    & $vitest run --config $viteConfig
    if ($LASTEXITCODE -ne 0) { throw '前端组件测试失败' }

    Write-Host '5/5 本地测试台生产构建' -ForegroundColor Cyan
    & $vite build --config $viteConfig
    if ($LASTEXITCODE -ne 0) { throw '本地测试台构建失败' }

    Write-Host '炸弹超人本地测试全部通过。' -ForegroundColor Green
} finally {
    Pop-Location
}
