@echo off
chcp 65001 >nul
echo ========================================
echo   AI数智化资产管理系统 - 启动脚本
echo ========================================
echo.

cd /d "%~dp0"

echo [1/3] 启动后端服务 (端口8000)...
start "AI-Asset-Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level warning"

timeout /t 3 /nobreak >nul

echo [2/3] 启动前端服务 (端口5173)...
start "AI-Asset-Frontend" cmd /k "cd /d %~dp0frontend && npx vite --host 0.0.0.0 --port 5173 --strictPort"

timeout /t 3 /nobreak >nul

echo [3/3] 启动完成！
echo.
echo 前端地址: http://localhost:5173
echo 后端地址: http://localhost:8000
echo API文档:  http://localhost:8000/docs
echo.
echo 登录账号: admin / admin123
echo.
echo 注意：请勿关闭弹出的两个命令行窗口，否则服务会停止
echo.
pause
