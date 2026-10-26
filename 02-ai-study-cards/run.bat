@echo off
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [错误] 还没有安装运行环境。
    echo 请先看 README.md 里的"安装依赖"一节，按步骤装一次。
    pause
    exit /b 1
)

if not exist ".env" (
    echo [提示] 没有找到 .env 文件。
    echo 请把 .env.example 复制一份改名为 .env，并填入你的 API Key。
    pause
    exit /b 1
)

echo 正在启动，浏览器会自动打开 http://127.0.0.1:7861
".venv\Scripts\python.exe" app.py
pause
