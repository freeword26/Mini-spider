@echo off
if "%1"=="start" goto start
if "%1"=="test" goto test
if "%1"=="validate" goto validate
if "%1"=="daily-ops" goto dailyops
echo Usage: make.bat [start^|test^|validate^|daily-ops]
goto end

:start
cd src && python start_unattended.py
goto end

:test
cd src && python -m pytest tests/ -v --tb=short
goto end

:validate
cd src && python -c "from unattended_validator import UnattendedValidator; v=UnattendedValidator(); r=v.validate_24_7_operation(); print(f'Validation: {r[\"uptime_score\"]}/100')"
goto end

:dailyops
cd src && python -c "import asyncio; from workflows.wf_daily_ops import DailyOpsWorkflow; from workflow_executor import WorkflowExecutor; from event_bus import create_event_bus; eb=create_event_bus({'mode':'memory'}); r=asyncio.run(DailyOpsWorkflow.execute(WorkflowExecutor(),{'base_path':'.'})); print(r)"
goto end

:end
