#!/usr/bin/env bash
set -euo pipefail

# =========================================
# AI Kill Cancer — Docker 部署腳本
# 用法: ./scripts/deploy.sh [環境]
#   環境: dev (預設) | staging | prod
# =========================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV="${1:-dev}"
COMPOSE_FILE="$PROJECT_DIR/docker/docker-compose.yml"

COLOR_INFO="\e[36m"
COLOR_OK="\e[32m"
COLOR_WARN="\e[33m"
COLOR_ERR="\e[31m"
COLOR_RESET="\e[0m"

info()  { echo -e "${COLOR_INFO}[INFO]${COLOR_RESET}  $*"; }
ok()    { echo -e "${COLOR_OK}[OK]${COLOR_RESET}    $*"; }
warn()  { echo -e "${COLOR_WARN}[WARN]${COLOR_RESET}  $*"; }
err()   { echo -e "${COLOR_ERR}[ERR]${COLOR_RESET}   $*"; }

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        err "部署失敗 (exit code: $exit_code)"
    fi
}
trap cleanup EXIT

check_prerequisites() {
    info "檢查必要工具..."

    if ! command -v docker &>/dev/null; then
        err "Docker 未安裝。請先安裝 Docker: https://docs.docker.com/get-docker/"
        exit 1
    fi
    ok "Docker $(docker --version | cut -d' ' -f3 | tr -d ',' )"

    if ! command -v docker-compose &>/dev/null && ! docker compose version &>/dev/null 2>&1; then
        err "Docker Compose 未安裝。"
        exit 1
    fi
    ok "Docker Compose 就緒"

    if [ ! -f "$COMPOSE_FILE" ]; then
        err "找不到 docker-compose.yml: $COMPOSE_FILE"
        exit 1
    fi
    ok "docker-compose.yml 存在"
}

set_env_file() {
    local env_file="$PROJECT_DIR/.env"
    local env_example="$PROJECT_DIR/.env.example"

    if [ ! -f "$env_file" ]; then
        if [ -f "$env_example" ]; then
            cp "$env_example" "$env_file"
            warn "已從 .env.example 建立 .env，請檢查設定"
        else
            warn "缺少 .env 檔案，將使用 docker-compose.yml 的預設值"
        fi
    else
        ok ".env 檔案存在"
    fi
}

set_env_profile() {
    case "$ENV" in
        dev)
            export COMPOSE_PROFILES=dev
            export LOG_LEVEL=DEBUG
            info "環境: 開發 (dev)"
            ;;
        staging)
            export COMPOSE_PROFILES=staging
            export LOG_LEVEL=INFO
            info "環境: 測試 (staging)"
            ;;
        prod)
            export COMPOSE_PROFILES=prod
            export LOG_LEVEL=WARNING
            export DEBUG=false
            info "環境: 生產 (prod)"
            ;;
        *)
            err "未知環境: $ENV (可用: dev, staging, prod)"
            exit 1
            ;;
    esac
}

build_images() {
    info "建構 Docker 映像..."
    docker compose -f "$COMPOSE_FILE" build --pull
    ok "映像建構完成"
}

deploy_services() {
    info "啟動服務..."
    docker compose -f "$COMPOSE_FILE" up -d
    ok "服務已啟動"
}

wait_health() {
    local service="$1"
    local max_retries=30
    local retry_interval=3

    info "等待 $service 就緒..."
    for i in $(seq 1 $max_retries); do
        local container_id
        container_id=$(docker compose -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null || true)
        if [ -z "$container_id" ]; then
            sleep "$retry_interval"
            continue
        fi
        local health_status
        health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_id" 2>/dev/null || echo "starting")
        if [ "$health_status" = "healthy" ]; then
            ok "$service 已就緒"
            return 0
        fi
        sleep "$retry_interval"
    done
    warn "$service 未在預期時間內就緒，請檢查日誌"
    return 1
}

check_services() {
    info "驗證服務健康狀態..."
    docker compose -f "$COMPOSE_FILE" ps

    wait_health db || true
    wait_health redis || true
    wait_health api || true
    wait_health frontend || true
}

show_info() {
    echo ""
    info "========================================"
    info "  AI Kill Cancer 部署完成"
    info "  環境: $ENV"
    info "  前端: http://localhost:${FRONTEND_PORT:-80}"
    info "  API:  http://localhost:${API_PORT:-8000}"
    info "  Docs: http://localhost:${API_PORT:-8000}/docs"
    info "========================================"
    echo ""
    info "查看日誌: docker compose -f \"$COMPOSE_FILE\" logs -f"
    info "停止服務: docker compose -f \"$COMPOSE_FILE\" down"
    info "重新啟動: docker compose -f \"$COMPOSE_FILE\" restart"
}

docker_compose_cmd() {
    if docker compose version &>/dev/null 2>&1; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

main() {
    echo ""
    info "=== AI Kill Cancer 部署腳本 (環境: $ENV) ==="
    echo ""

    check_prerequisites
    set_env_profile
    set_env_file
    build_images
    deploy_services
    check_services
    show_info
}

main
