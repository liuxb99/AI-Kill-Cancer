#!/bin/bash
set -euo pipefail

# ============================================================
# AI Kill Cancer - System Monitor Script
# ============================================================
# Usage:
#   ./scripts/monitor.sh                # Run all checks
#   ./scripts/monitor.sh --health       # Health check only
#   ./scripts/monitor.sh --metrics      # Print metrics to stdout
#   ./scripts/monitor.sh --alert        # Alert if thresholds exceeded
#   ./scripts/monitor.sh --daemon       # Run as monitoring daemon
# ============================================================

APP_NAME="ai-kill-cancer"
APP_PORT=8000
METRICS_DIR="/var/log/${APP_NAME}/metrics"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"
THRESHOLD_CPU=90
THRESHOLD_MEM=85
THRESHOLD_DISK=90
THRESHOLD_LATENCY_MS=5000
CHECK_INTERVAL=60

mkdir -p "$METRICS_DIR"

log() {
    local level="$1"
    local msg="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [${level}] ${msg}"
}

check_health() {
    log "INFO" "Checking health endpoint..."
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        "http://localhost:${APP_PORT}/health" 2>/dev/null || echo "000")

    if [ "$status" = "200" ]; then
        log "OK" "Health check passed (HTTP 200)"
        return 0
    else
        log "ERROR" "Health check failed (HTTP ${status})"
        return 1
    fi
}

check_container() {
    log "INFO" "Checking container status..."
    if docker ps --format "{{.Names}}" | grep -q "^${APP_NAME}$"; then
        local uptime
        uptime=$(docker inspect --format='{{.State.StartedAt}}' "$APP_NAME" 2>/dev/null)
        log "OK" "Container '${APP_NAME}' is running (since ${uptime})"
        return 0
    else
        log "ERROR" "Container '${APP_NAME}' is NOT running"
        return 1
    fi
}

collect_metrics() {
    local timestamp
    timestamp=$(date '+%Y%m%d_%H%M%S')
    local metrics_file="${METRICS_DIR}/metrics_${timestamp}.json"

    log "INFO" "Collecting system metrics..."

    local cpu_usage mem_usage disk_usage latency_p99

    cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print 100 - $8}' | head -1)
    mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')
    disk_usage=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
    latency_p99=$(curl -s --max-time 5 \
        "http://localhost:${APP_PORT}/metrics" 2>/dev/null \
        | grep 'http_request_duration_seconds.*quantile="0.99"' \
        | awk '{print $2}' || echo "0")

    local http_2xx http_4xx http_5xx rps
    http_2xx=$(curl -s --max-time 5 \
        "http://localhost:${APP_PORT}/metrics" 2>/dev/null \
        | grep 'http_requests_total.*status="2"' \
        | awk '{sum+=$NF} END{print sum+0}' || echo "0")
    http_5xx=$(curl -s --max-time 5 \
        "http://localhost:${APP_PORT}/metrics" 2>/dev/null \
        | grep 'http_requests_total.*status="5"' \
        | awk '{sum+=$NF} END{print sum+0}' || echo "0")

    cat > "$metrics_file" << EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "hostname": "$(hostname)",
  "app": "${APP_NAME}",
  "metrics": {
    "cpu_usage_pct": ${cpu_usage:-0},
    "memory_usage_pct": ${mem_usage:-0},
    "disk_usage_pct": ${disk_usage:-0},
    "latency_p99_ms": ${latency_p99:-0},
    "http_2xx": ${http_2xx:-0},
    "http_5xx": ${http_5xx:-0}
  }
}
EOF

    log "OK" "Metrics saved to ${metrics_file}"
    cat "$metrics_file"
}

check_thresholds() {
    log "INFO" "Checking thresholds..."
    local metrics_file
    metrics_file=$(ls -t "${METRICS_DIR}"/metrics_*.json 2>/dev/null | head -1)

    if [ -z "$metrics_file" ]; then
        log "WARN" "No metrics file found, collecting first..."
        collect_metrics > /dev/null
        metrics_file=$(ls -t "${METRICS_DIR}"/metrics_*.json 2>/dev/null | head -1)
    fi

    local cpu mem disk latency
    cpu=$(python3 -c "import json; d=json.load(open('${metrics_file}')); print(d['metrics']['cpu_usage_pct'])" 2>/dev/null || echo "0")
    mem=$(python3 -c "import json; d=json.load(open('${metrics_file}')); print(d['metrics']['memory_usage_pct'])" 2>/dev/null || echo "0")
    disk=$(python3 -c "import json; d=json.load(open('${metrics_file}')); print(d['metrics']['disk_usage_pct'])" 2>/dev/null || echo "0")
    latency=$(python3 -c "import json; d=json.load(open('${metrics_file}')); print(d['metrics']['latency_p99_ms'])" 2>/dev/null || echo "0")

    local alert_msg=""
    local has_alert=false

    if (( $(echo "$cpu > $THRESHOLD_CPU" | bc -l) )); then
        alert_msg="${alert_msg}CPU at ${cpu}% (threshold: ${THRESHOLD_CPU}%) | "
        has_alert=true
    fi
    if (( $(echo "$mem > $THRESHOLD_MEM" | bc -l) )); then
        alert_msg="${alert_msg}Memory at ${mem}% (threshold: ${THRESHOLD_MEM}%) | "
        has_alert=true
    fi
    if (( $(echo "$disk > $THRESHOLD_DISK" | bc -l) )); then
        alert_msg="${alert_msg}Disk at ${disk}% (threshold: ${THRESHOLD_DISK}%) | "
        has_alert=true
    fi
    if (( $(echo "$latency > $THRESHOLD_LATENCY_MS" | bc -l) )); then
        alert_msg="${alert_msg}Latency P99 at ${latency}ms (threshold: ${THRESHOLD_LATENCY_MS}ms) | "
        has_alert=true
    fi

    if [ "$has_alert" = true ]; then
        log "ALERT" "${alert_msg% | }"
        send_alert "${alert_msg% | }"
        return 1
    else
        log "OK" "All metrics within thresholds (CPU: ${cpu}%, Mem: ${mem}%, Disk: ${disk}%, Latency: ${latency}ms)"
        return 0
    fi
}

send_alert() {
    local message="$1"
    local hostname
    hostname=$(hostname)

    if [ -n "$ALERT_WEBHOOK" ]; then
        log "INFO" "Sending alert to webhook..."
        curl -s -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{
                \"text\": \"[${APP_NAME}] ALERT on ${hostname}\n${message}\nTime: $(date -u +%Y-%m-%dT%H:%M:%SZ)\"
            }" > /dev/null 2>&1 || log "WARN" "Failed to send webhook alert"
    fi

    logger -t "${APP_NAME}-monitor" "ALERT: ${message}"
}

cleanup_metrics() {
    local retention_days=7
    log "INFO" "Cleaning up metrics older than ${retention_days} days..."
    find "$METRICS_DIR" -name "metrics_*.json" -mtime +${retention_days} -delete
    log "OK" "Cleanup complete"
}

daemon_loop() {
    log "INFO" "Starting monitor daemon (interval: ${CHECK_INTERVAL}s)..."
    while true; do
        check_health || true
        check_container || true
        collect_metrics > /dev/null
        check_thresholds || true
        cleanup_metrics
        sleep "$CHECK_INTERVAL"
    done
}

print_metrics() {
    collect_metrics
}

case "${1:-}" in
    --health)
        check_health
        check_container
        ;;
    --metrics)
        print_metrics
        ;;
    --alert)
        collect_metrics > /dev/null
        check_thresholds
        ;;
    --daemon)
        daemon_loop
        ;;
    *)
        check_health
        check_container
        collect_metrics
        check_thresholds
        cleanup_metrics
        ;;
esac
