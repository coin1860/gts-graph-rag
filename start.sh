#!/bin/bash

# 获取当前脚本所在目录的绝对路径
ROOT_DIR=$(pwd)

# 定义日志文件路径
BACKEND_LOG="$ROOT_DIR/backend.log"
FRONTEND_LOG="$ROOT_DIR/frontend.log"

echo "🚀 正在启动项目..."

# 1. 启动后端
# 使用 nohup 后台运行，并将标准输出(1)和错误输出(2)都写入 backend.log
echo "正在启动后端 (uv run)... 日志输出至 $BACKEND_LOG"
nohup uv run python -m backend.server > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# 2. 启动前端
# 进入 frontend 目录启动，并将日志输出至 frontend.log
echo "正在启动前端 (npm run dev)... 日志输出至 $FRONTEND_LOG"
(
    cd frontend
    nohup npm run dev > "$FRONTEND_LOG" 2>&1 &
)
FRONTEND_PID=$!

echo "---------------------------------------"
echo "✅ 启动成功！"
echo "后端 PID: $BACKEND_PID"
echo "前端 PID: $FRONTEND_PID"
echo "使用 'tail -f backend.log' 查看后端实时日志"
echo "使用 'kill $BACKEND_PID $FRONTEND_PID' 停止服务"
echo "---------------------------------------"

