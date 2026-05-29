#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无人值守架构验证器测试"""

import sys
import json
import io
from pathlib import Path

if sys.platform == "win32":
    import os
    os.environ["PYTHONIOENCODING"] = "utf-8"

# Add workflow dir to path
wf_dir = Path(__file__).parent.parent
sys.path.insert(0, str(wf_dir))

from unattended_event_scheduler import TwentyTwoProjectScheduler


def test_scheduler_init():
    scheduler = TwentyTwoProjectScheduler(event_bus=None)
    assert scheduler is not None


def test_22_projects_configured():
    scheduler = TwentyTwoProjectScheduler(event_bus=None)
    status = scheduler.get_schedule_status()
    assert status["total_projects"] == 22, f"Expected 22, got {status['total_projects']}"
    assert "P001_TAPD" in TwentyTwoProjectScheduler.PROJECT_SCHEDULES
    assert "P022_fast_dev" in TwentyTwoProjectScheduler.PROJECT_SCHEDULES


def test_three_layers():
    scheduler = TwentyTwoProjectScheduler(event_bus=None)
    layers = set()
    for pid, cfg in TwentyTwoProjectScheduler.PROJECT_SCHEDULES.items():
        layers.add(cfg.get("layer"))
    assert "指挥控制层" in layers
    assert "执行协作层" in layers
    assert "资源与环境层" in layers


def test_p0_priority():
    scheduler = TwentyTwoProjectScheduler(event_bus=None)
    p0_count = sum(
        1 for cfg in TwentyTwoProjectScheduler.PROJECT_SCHEDULES.values()
        if cfg.get("priority") == "P0"
    )
    assert p0_count > 0, "Should have at least one P0 project"


def test_scheduler_status():
    scheduler = TwentyTwoProjectScheduler(event_bus=None)
    status = scheduler.get_schedule_status()
    assert "total_projects" in status
    assert "total_jobs" in status
    assert "layer_distribution" in status
    assert "priority_distribution" in status


def test_validator_runs():
    from unattended_validator import UnattendedValidator
    validator = UnattendedValidator()
    result = validator.validate_24_7_operation()
    assert "uptime_score" in result
    assert "details" in result
    assert "deployment_readiness" in result
    assert result["uptime_score"] >= 0


def test_event_bus_rabbitmq():
    from event_bus import RabbitMQEventBus, create_event_bus
    eb = create_event_bus({"mode": "memory"})
    assert eb is not None


def test_auth_gateway():
    from auth_gateway import UserAuthorizationManager, CRITICAL_OPERATIONS
    auth = UserAuthorizationManager()
    stats = auth.get_authorization_stats()
    assert stats["total_requests"] == 0
    assert len(CRITICAL_OPERATIONS) > 0


def test_self_healing():
    from self_healing import SelfHealing, HealingAction
    sh = SelfHealing()
    stats = sh.get_healing_stats()
    assert "total_healing_actions" in stats


def test_astrbot_gateway():
    from astrbot_gateway_adapter import (
        AstrBotGatewayAdapter, IntentType, RecognizedIntent
    )
    adapter = AstrBotGatewayAdapter()
    intent = adapter.recognize_intent("查看任务分配状态")
    assert intent is not None


def test_file_access_layer():
    from file_access_layer import FileAccessLayer
    fal = FileAccessLayer()
    stats = fal.get_stats()
    assert "total_access" in stats
    assert "whitelist_entries" in stats


def test_report_generator():
    from report_generator import ReportGenerator, PROJECT_NAMES
    rg = ReportGenerator()
    report = rg.generate_daily_progress_report()
    assert "每日项目进度报告" in report
    assert len(PROJECT_NAMES) == 22


def test_monitoring_three_layer():
    from monitoring import Monitoring
    from event_bus import create_event_bus
    eb = create_event_bus({"mode": "memory"})
    mon = Monitoring(event_bus=eb)
    health = mon.check_three_layer_health()
    assert "overall_status" in health
    assert "layers" in health
    assert "指挥控制层" in health["layers"]


def test_config_has_eventbus():
    from config import EventBusConfig, AstrBotGatewayConfig, Config
    eb_cfg = EventBusConfig()
    assert eb_cfg.mode in ("memory", "rabbitmq")
    astr_cfg = AstrBotGatewayConfig()
    assert astr_cfg.low_token_mode is True
    cfg = Config()
    assert cfg.event_bus is not None
    assert cfg.astrbot_gateway is not None


def _icon(status):
    return "[OK]" if status == "pass" else "[ERR]"


if __name__ == "__main__":
    import traceback

    tests = [
        test_scheduler_init,
        test_22_projects_configured,
        test_three_layers,
        test_p0_priority,
        test_scheduler_status,
        test_validator_runs,
        test_event_bus_rabbitmq,
        test_auth_gateway,
        test_self_healing,
        test_astrbot_gateway,
        test_file_access_layer,
        test_report_generator,
        test_monitoring_three_layer,
        test_config_has_eventbus,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  {True} {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  {False} {test.__name__}: {e}")
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 50}")
    print(f"Tests: {passed} passed, {failed} failed, {passed + failed} total")
    if failed == 0:
        print("All tests PASSED [OK]")
    else:
        print(f"Some tests FAILED [ERR]")
    sys.exit(0 if failed == 0 else 1)
