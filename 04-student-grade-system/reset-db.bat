@echo off
chcp 65001 >nul
title 重置数据库

echo ============================================
echo   重置学生成绩管理系统数据库
echo ============================================
echo.
echo 此操作会：
echo   1. 停止正在运行的服务
echo   2. 删除数据库文件
echo   3. 下次启动时自动重新初始化演示数据
echo.
echo 所有手动录入的数据将会丢失！
echo.
set /p CONFIRM=确定要重置吗？(Y/N):
if /i not "%CONFIRM%"=="Y" (
    echo 已取消。
    timeout /t 2 /nobreak >nul
    exit /b 0
)

echo.
echo 停止服务...
taskkill /FI "WINDOWTITLE eq 学生成绩管理系统-后端*" /T /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8080" ^| findstr "LISTENING"') do (
    taskkill /PID %%a /T /F >nul 2>&1
)
timeout /t 2 /nobreak >nul

echo 删除数据库文件...
if exist "%~dp0backend\data" (
    rmdir /s /q "%~dp0backend\data"
    echo   已删除 backend\data
) else (
    echo   数据库目录不存在，无需删除
)

echo.
echo ============================================
echo   重置完成！
echo   请运行 start.bat 重新启动系统
echo ============================================
echo.
timeout /t 4 /nobreak >nul
