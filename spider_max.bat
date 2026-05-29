@echo off
chcp 65001 >nul 2>&1
title spider_max v3.0 - 全栈项目管理与多Agent协同平台
color 0A

cd /d "%~dp0"

echo.
echo ================================================================
echo   Spider Max / 大蜘蛛  v3.0
echo   全栈项目管理 · 多Agent协同 · OKR · DAG · 数据分析
echo ================================================================
echo.

echo [检查] Python环境...
set PYTHON=
python3.14 --version >nul 2>&1 && set PYTHON=python3.14 && goto :found
python3 --version >nul 2>&1 && set PYTHON=python3 && goto :found
python --version >nul 2>&1 && set PYTHON=python && goto :found
echo [错误] 未找到Python 3.10+
pause
exit /b 1

:found
echo [OK] Python: %PYTHON%

echo [检查] 依赖包...
%PYTHON% -m pip install click rich fastapi uvicorn pika schedule croniter psutil -q 2>nul
echo [OK] 依赖就绪

echo.
echo ================================================================
echo  CLI命令:
echo    spider-max start      启动全套服务
echo    spider-max status     查看系统状态
echo    spider-max validate   架构验证
echo    spider-max agents     查看Agent注册表
echo    spider-max schedule   调度器状态
echo ================================================================
echo.

%PYTHON% run.py --help

echo.
pause
