@echo off
chcp 65001 >nul
cd /d %~dp0

if not exist .venv (
    echo [1/3] 创建虚拟环境...
    python -m venv .venv
)

echo [2/3] 安装依赖（首次较慢，之后很快）...
call .venv\Scripts\python.exe -m pip install -q -r requirements.txt

if not exist .env (
    echo [提示] 还没有 .env，请把 .env.example 复制为 .env 并填入 LLM_API_KEY
)

echo [3/3] 启动服务...
call .venv\Scripts\python.exe app.py
pause
