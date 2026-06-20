@echo off
echo ========================================
echo 模板支撑验算后端服务 - 启动脚本
echo ========================================
echo.

echo [1/2] 检查 Python 环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

echo.
echo [2/2] 启动服务...
echo 服务将在 http://127.0.0.1:8000 启动
echo API 文档: http://127.0.0.1:8000/docs
echo.
echo 按 Ctrl+C 停止服务
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
