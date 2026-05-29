.PHONY: start install test validate docker

install:
	pip install -r src/requirements.txt
	pip install -e .

start:
	cd src && python start_unattended.py

test:
	cd src && python3.14 -m pytest tests/ -v --tb=short

validate:
	cd src && python3.14 -c "from unattended_validator import UnattendedValidator; v=UnattendedValidator(); r=v.validate_24_7_operation(); print(f'Validation: {r[\"uptime_score\"]}/100')"

daily-ops:
	cd src && python3.14 -c "import asyncio; from workflows.wf_daily_ops import DailyOpsWorkflow; from workflow_executor import WorkflowExecutor; eb=__import__('event_bus',fromlist=['create_event_bus']).create_event_bus({'mode':'memory'}); r=asyncio.run(DailyOpsWorkflow.execute(WorkflowExecutor(),{'base_path':'.'})); print(r)"
