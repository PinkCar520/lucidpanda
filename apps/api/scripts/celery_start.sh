#!/bin/bash
# Celery 快速启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================="
echo "  LucidPanda Celery 启动脚本"
echo "=========================================="

# 检查依赖
check_dependencies() {
    echo "📋 检查依赖..."
    
    if ! command -v docker &> /dev/null; then
        echo "❌ Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker compose &> /dev/null; then
        echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    echo "✅ Docker 和 Docker Compose 已安装"
}

# 检查.env 文件
check_env() {
    echo "📋 检查环境配置..."
    
    if [ ! -f ".env" ]; then
        echo "⚠️  .env 文件不存在，正在创建..."
        cp .env.example .env
        echo "✅ 已创建 .env 文件，请配置必要的环境变量"
        echo "   特别是：POSTGRES_PASSWORD, AUTH_SECRET, REDIS_URL"
        exit 1
    fi
    
    echo "✅ .env 文件存在"
}

# 运行数据库迁移
run_migration() {
    echo "📋 运行数据库迁移..."
    
    # 检查数据库是否运行
    if ! docker compose ps | grep -q "lucidpanda_db.*Up"; then
        echo "⚠️  数据库未运行，正在启动..."
        docker compose up -d db redis
        sleep 5
    fi
    
    # 运行迁移
    docker compose run --rm \
        -e DB_TYPE=postgres \
        -e POSTGRES_HOST=db \
        celery_worker \
        python scripts/migrations/create_feed_statistics_table.py
    
    echo "✅ 数据库迁移完成"
}

# 启动 Celery 服务
start_celery() {
    echo "📋 启动 Celery 服务..."
    
    # 停止旧版 collector
    echo "⏹️  停止旧版 Collector..."
    docker compose stop collector 2>/dev/null || true
    
    # 启动 Celery Beat + Worker
    echo "🚀 启动 Celery Beat + Worker..."
    docker compose up -d celery_beat celery_worker
    
    # 等待启动
    sleep 3
    
    # 检查状态
    echo ""
    echo "📊 服务状态:"
    docker compose ps celery_beat celery_worker
    
    echo ""
    echo "=========================================="
    echo "  ✅ Celery 服务启动成功!"
    echo "=========================================="
    echo ""
    echo "查看日志:"
    echo "  docker compose logs -f celery_beat"
    echo "  docker compose logs -f celery_worker"
    echo ""
    echo "启动监控 UI (可选):"
    echo "  docker compose --profile monitoring up -d celery_flower"
    echo "  访问：http://localhost:5555"
    echo ""
}

# 显示帮助
show_help() {
    echo "用法：$0 [command]"
    echo ""
    echo "Commands:"
    echo "  start       启动 Celery 服务 (默认)"
    echo "  stop        停止 Celery 服务"
    echo "  restart     重启 Celery 服务"
    echo "  status      查看服务状态"
    echo "  logs        查看日志"
    echo "  migrate     运行数据库迁移"
    echo "  flower      启动 Flower 监控 UI"
    echo "  help        显示帮助信息"
    echo ""
}

# 停止 Celery 服务
stop_celery() {
    echo "⏹️  停止 Celery 服务..."
    docker compose stop celery_beat celery_worker celery_flower
    echo "✅ Celery 服务已停止"
}

# 重启 Celery 服务
restart_celery() {
    stop_celery
    sleep 2
    start_celery
}

# 查看状态
show_status() {
    echo "📊 Celery 服务状态:"
    echo ""
    docker compose ps celery_beat celery_worker celery_flower
}

# 查看日志
show_logs() {
    docker compose logs -f celery_beat celery_worker
}

# 启动 Flower
start_flower() {
    echo "🚀 启动 Flower 监控 UI..."
    docker compose --profile monitoring up -d celery_flower
    echo ""
    echo "✅ Flower 已启动"
    echo "   访问：http://localhost:5555"
}

# 主逻辑
main() {
    case "${1:-start}" in
        start)
            check_dependencies
            check_env
            run_migration
            start_celery
            ;;
        stop)
            stop_celery
            ;;
        restart)
            restart_celery
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs
            ;;
        migrate)
            run_migration
            ;;
        flower)
            start_flower
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo "❌ 未知命令：$1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
