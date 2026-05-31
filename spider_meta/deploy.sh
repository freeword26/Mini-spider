#!/usr/bin/env bash
# ============================================================
# spider_meta Docker 部署脚本
# 用法:
#   ./deploy.sh up       # 启动所有服务
#   ./deploy.sh down     # 停止所有服务
#   ./deploy.sh build    # 重新构建镜像
#   ./deploy.sh logs     # 查看日志
#   ./deploy.sh status   # 查看服务状态
#   ./deploy.sh test     # 运行测试
# ============================================================

set -e

COMPOSE_FILE="docker-compose.yml"
PROJECT_NAME="spider_meta"

case "${1:-up}" in
  up)
    echo "🚀 启动 spider_meta 服务..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" up -d --build
    echo ""
    echo "✅ 服务已启动"
    echo "   API 地址: http://localhost:8003"
    echo "   健康检查: http://localhost:8003/health"
    echo "   指标监控: http://localhost:8003/metrics"
    echo ""
    echo "📋 查看日志: $0 logs"
    ;;

  down)
    echo "🛑 停止 spider_meta 服务..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" down
    echo "✅ 服务已停止"
    ;;

  build)
    echo "🔨 重新构建镜像..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" build --no-cache
    echo "✅ 构建完成"
    ;;

  logs)
    echo "📋 查看日志 (Ctrl+C 退出)..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" logs -f
    ;;

  status)
    echo "📊 服务状态:"
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" ps
    echo ""
    echo "🔍 API 健康状态:"
    curl -s http://localhost:8003/health 2>/dev/null | python3 -m json.tool 2>/dev/null || echo "   API 未响应"
    ;;

  test)
    echo "🧪 运行测试..."
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT_NAME" run --rm api \
      python -m pytest tests/ -v --tb=short
    ;;

  *)
    echo "用法: $0 {up|down|build|logs|status|test}"
    exit 1
    ;;
esac
