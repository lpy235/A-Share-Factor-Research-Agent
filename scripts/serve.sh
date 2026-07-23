#!/usr/bin/env bash
# A股因子研究服务 一键开关脚本
# 用法: ./scripts/serve.sh {up|down|toggle|restart|status|logs}
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

HOST="127.0.0.1"
PORT="8000"
UVICORN=".venv/bin/uvicorn"
APP_MODULE="app.main:app"
PID_FILE=".serve.pid"
LOG_FILE=".serve.log"

if [[ -t 1 ]]; then
  GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[0;33m'
  CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'
else
  GREEN=''; RED=''; YELLOW=''; CYAN=''; BOLD=''; RESET=''
fi

port_pid() { lsof -ti:"$PORT" 2>/dev/null || true; }
recorded_pid() { [[ -f "$PID_FILE" ]] && cat "$PID_FILE" 2>/dev/null || true; }
is_running() {
  local pid
  pid="$(recorded_pid)"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

cmd_up() {
  if is_running; then
    echo -e "${YELLOW}⚠ 服务已在运行${RESET}  PID=$(recorded_pid)  http://${HOST}:${PORT}/"
    return 0
  fi
  rm -f "$PID_FILE"
  local occ
  occ="$(port_pid)"
  if [[ -n "$occ" ]]; then
    echo -e "${RED}✘ 端口 ${PORT} 已被其他进程占用 (PID=${occ})${RESET}"
    echo "  请先释放该端口,或修改 scripts/serve.sh 中的 PORT"
    return 1
  fi
  if [[ ! -x "$UVICORN" ]]; then
    echo -e "${RED}✘ 未找到 ${UVICORN}${RESET}"
    echo "  请先运行: python -m venv .venv && .venv/bin/pip install -e ."
    return 1
  fi
  echo -e "${CYAN}▶ 启动研究服务...${RESET}"
  nohup "$UVICORN" "$APP_MODULE" --host "$HOST" --port "$PORT" > "$LOG_FILE" 2>&1 &
  echo $! > "$PID_FILE"
  local i=0
  while [[ $i -lt 30 ]]; do
    if curl -sf "http://${HOST}:${PORT}/health" >/dev/null 2>&1; then
      echo -e "${GREEN}✔ 服务已启动${RESET}  PID=$(recorded_pid)"
      echo -e "  面板: ${BOLD}http://${HOST}:${PORT}/${RESET}"
      echo -e "  接口: http://${HOST}:${PORT}/docs"
      echo -e "  日志: tail -f ${LOG_FILE}"
      return 0
    fi
    if ! kill -0 "$(recorded_pid)" 2>/dev/null; then
      echo -e "${RED}✘ 服务启动失败,日志末尾:${RESET}"
      tail -n 20 "$LOG_FILE" 2>/dev/null || true
      rm -f "$PID_FILE"
      return 1
    fi
    sleep 0.5
    i=$((i + 1))
  done
  echo -e "${YELLOW}⚠ 启动超时(15s),请检查日志: tail -f ${LOG_FILE}${RESET}"
  return 1
}

cmd_down() {
  if ! is_running; then
    rm -f "$PID_FILE"
    echo -e "${YELLOW}⚠ 服务未在运行${RESET}"
    return 0
  fi
  local pid
  pid="$(recorded_pid)"
  echo -e "${CYAN}■ 停止服务 PID=${pid}...${RESET}"
  kill -TERM "$pid" 2>/dev/null || true
  local i=0
  while [[ $i -lt 20 ]]; do
    if ! kill -0 "$pid" 2>/dev/null; then break; fi
    sleep 0.25
    i=$((i + 1))
  done
  if kill -0 "$pid" 2>/dev/null; then
    echo -e "${YELLOW}强制终止...${RESET}"
    kill -KILL "$pid" 2>/dev/null || true
  fi
  rm -f "$PID_FILE"
  echo -e "${GREEN}✔ 服务已停止${RESET}"
}

cmd_status() {
  if is_running; then
    echo -e "${GREEN}● 运行中${RESET}  PID=$(recorded_pid)  http://${HOST}:${PORT}/"
  else
    rm -f "$PID_FILE" 2>/dev/null || true
    echo -e "${RED}○ 未运行${RESET}"
  fi
}

cmd_toggle() {
  if is_running; then cmd_down; else cmd_up; fi
}

cmd_logs() {
  if [[ -f "$LOG_FILE" ]]; then
    tail -n 50 "$LOG_FILE"
  else
    echo "无日志文件 (${LOG_FILE})"
  fi
}

usage() {
  cat <<EOF
A股因子研究服务开关
用法: ./scripts/serve.sh <命令>

命令:
  up        启动服务(后台运行)
  down      停止服务
  toggle    一键切换(运行中→停,未运行→启)  [默认]
  restart   重启
  status    查看状态
  logs      查看最近日志
EOF
}

case "${1:-toggle}" in
  up) cmd_up ;;
  down) cmd_down ;;
  toggle) cmd_toggle ;;
  restart) cmd_down || true; cmd_up ;;
  status) cmd_status ;;
  logs) cmd_logs ;;
  *) usage; exit 1 ;;
esac
