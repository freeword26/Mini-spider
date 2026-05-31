# ============================================================
# spider_meta Docker 部署脚本 (Windows PowerShell)
# 用法:
#   .\deploy.ps1 up       # 启动所有服务
#   .\deploy.ps1 down     # 停止所有服务
#   .\deploy.ps1 build    # 重新构建镜像
#   .\deploy.ps1 logs     # 查看日志
#   .\deploy.ps1 status   # 查看服务状态
#   .\deploy.ps1 test     # 运行测试
# ============================================================

param(
    [Parameter(Position=0)]
    [ValidateSet("up", "down", "build", "logs", "status", "test")]
    [string]$Action = "up"
)

$ComposeFile = "docker-compose.yml"
$ProjectName = "spider_meta"

switch ($Action) {
    "up" {
        Write-Host "🚀 启动 spider_meta 服务..." -ForegroundColor Green
        docker compose -f $ComposeFile -p $ProjectName up -d --build
        Write-Host ""
        Write-Host "✅ 服务已启动" -ForegroundColor Green
        Write-Host "   API 地址: http://localhost:8003"
        Write-Host "   健康检查: http://localhost:8003/health"
        Write-Host "   指标监控: http://localhost:8003/metrics"
    }
    "down" {
        Write-Host "🛑 停止 spider_meta 服务..." -ForegroundColor Yellow
        docker compose -f $ComposeFile -p $ProjectName down
        Write-Host "✅ 服务已停止" -ForegroundColor Green
    }
    "build" {
        Write-Host "🔨 重新构建镜像..." -ForegroundColor Cyan
        docker compose -f $ComposeFile -p $ProjectName build --no-cache
        Write-Host "✅ 构建完成" -ForegroundColor Green
    }
    "logs" {
        Write-Host "📋 查看日志 (Ctrl+C 退出)..." -ForegroundColor Cyan
        docker compose -f $ComposeFile -p $ProjectName logs -f
    }
    "status" {
        Write-Host "📊 服务状态:" -ForegroundColor Cyan
        docker compose -f $ComposeFile -p $ProjectName ps
        Write-Host ""
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:8003/health" -TimeoutSec 5
            Write-Host "🔍 API 健康状态:" -ForegroundColor Green
            $health | ConvertTo-Json
        } catch {
            Write-Host "   API 未响应" -ForegroundColor Red
        }
    }
    "test" {
        Write-Host "🧪 运行测试..." -ForegroundColor Cyan
        docker compose -f $ComposeFile -p $ProjectName run --rm api `
            python -m pytest tests/ -v --tb=short
    }
}
