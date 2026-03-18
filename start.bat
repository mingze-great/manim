@echo off
echo ========================================
echo   Manim Platform 启动脚本
echo ========================================
echo.

echo [1/2] Starting Backend...
cd /d %~dp0backend
start "Backend" cmd /k "python -m uvicorn app.main:app --reload --log-level debug"

echo [2/2] Starting Frontend...
cd /d %~dp0frontend
start "Frontend" cmd /k "npm run dev"

echo.
echo ========================================
echo   已启动两个窗口:
echo   - Backend (后端日志)
echo   - Frontend (前端日志)
echo ========================================
echo.
echo 请在浏览器中打开: http://localhost:5173
pause
