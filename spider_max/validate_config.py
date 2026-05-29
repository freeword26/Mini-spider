"""
Agent配置验证脚本 - 无人值守系统
"""

import sys
import json
from pathlib import Path
from datetime import datetime, time

# 添加当前目录到路径
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))


def validate_agent_registry():
    """验证Agent注册表"""
    print("=" * 60)
    print("验证Agent注册表...")
    print("=" * 60)
    
    try:
        from agents import agent_registry, AgentStatus
        
        # 获取所有Agent
        agents = agent_registry.get_all_agents()
        print(f"\n✅ 成功加载 {len(agents)} 个Agent:")
        
        for agent in agents:
            print(f"\n  - {agent.agent_id} ({agent.name})")
            print(f"    权限级别: {agent.permission_level}")
            print(f"    状态: {agent.status.value}")
            print(f"    分配工作流: {agent.assigned_workflows}")
            print(f"    技能: {agent.skills}")
        
        # 测试获取Agent
        test_agent = agent_registry.get_agent("system-manager")
        if test_agent:
            print(f"\n✅ 成功获取指定Agent: {test_agent.name}")
        
        # 测试获取工作流分配
        wf_agents = agent_registry.get_agents_by_workflow("WF-001")
        print(f"\n✅ 分配到WF-001的Agent: {[a.name for a in wf_agents]}")
        
        # 测试转换为字典
        registry_dict = agent_registry.to_dict()
        print(f"\n✅ 成功转换为字典格式，包含 {len(registry_dict)} 个Agent")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Agent注册表验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_daily_schedule():
    """验证每日排班"""
    print("\n" + "=" * 60)
    print("验证每日排班...")
    print("=" * 60)
    
    try:
        from agents.schedules import daily_schedule
        
        print(f"\n✅ 成功加载每日排班配置")
        print(f"\n时间槽配置 ({len(daily_schedule.time_slots)} 个):")
        for i, slot in enumerate(daily_schedule.time_slots, 1):
            print(f"\n  {i}. {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}")
            print(f"     Agent: {slot.agent_id}")
            print(f"     工作流: {slot.assigned_workflows}")
            print(f"     其他职责: {slot.other_duties}")
        
        print(f"\n全天候Agent ({len(daily_schedule.always_on_agents)} 个):")
        for agent in daily_schedule.always_on_agents:
            print(f"  - {agent['agent_id']}: {agent['other_duties']}")
        
        # 测试获取当前时间槽
        current_time = datetime.now().time()
        current_slot = daily_schedule.get_current_slot(current_time)
        if current_slot:
            print(f"\n✅ 当前时间 ({current_time.strftime('%H:%M')}) 的当班Agent: {current_slot.agent_id}")
        
        # 测试获取当班Agent列表
        on_duty = daily_schedule.get_on_duty_agents(current_time)
        print(f"✅ 当前所有当班Agent: {on_duty}")
        
        # 测试转换为字典
        schedule_dict = daily_schedule.to_dict()
        print(f"\n✅ 成功转换为字典格式")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 每日排班验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_weekly_schedule():
    """验证周排班"""
    print("\n" + "=" * 60)
    print("验证周排班...")
    print("=" * 60)
    
    try:
        from agents.schedules import weekly_schedule
        
        print(f"\n✅ 成功加载周排班配置")
        print(f"\n总排班槽数: {len(weekly_schedule.slots)}")
        
        # 测试获取指定周几的排班
        day_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
        today = datetime.now().weekday()
        today_slots = weekly_schedule.get_slots_for_day(today)
        print(f"\n✅ {day_names[today]} 的排班 ({len(today_slots)} 个):")
        for slot in today_slots:
            print(f"  - {slot.time_str}: {slot.agent_id} - {slot.special_note}")
        
        # 测试转换为字典
        weekly_dict = weekly_schedule.to_dict()
        print(f"\n✅ 成功转换为字典格式")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 周排班验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_json_config():
    """验证JSON配置文件"""
    print("\n" + "=" * 60)
    print("验证JSON配置文件...")
    print("=" * 60)
    
    try:
        config_file = current_dir / "agent_config.json"
        
        if not config_file.exists():
            print(f"\n❌ 配置文件不存在: {config_file}")
            return False
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print(f"\n✅ 成功加载JSON配置文件")
        print(f"   版本: {config.get('version')}")
        print(f"   创建时间: {config.get('created_at')}")
        print(f"   描述: {config.get('description')}")
        
        # 验证Agent配置
        agents_config = config.get("agents", {})
        print(f"\n✅ Agent配置: {len(agents_config)} 个")
        
        # 验证每日排班
        daily_config = config.get("daily_schedule", {})
        print(f"✅ 每日排班配置: {len(daily_config.get('time_slots', []))} 个时间槽")
        
        # 验证周排班
        weekly_config = config.get("weekly_schedule", {})
        print(f"✅ 周排班配置: {len(weekly_config.get('slots', []))} 个时间槽")
        
        # 验证技术管理配置
        tech_config = config.get("technical_management", {})
        print(f"✅ 技术管理配置已加载")
        print(f"   容错机制: {list(tech_config.get('fault_tolerance', {}).keys())}")
        print(f"   KPI指标: {len(tech_config.get('kpis', {}))} 个")
        
        return True
        
    except Exception as e:
        print(f"\n❌ JSON配置验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("无人值守系统 Agent配置验证")
    print("=" * 60)
    
    results = []
    
    # 验证Agent注册表
    results.append(("Agent注册表", validate_agent_registry()))
    
    # 验证每日排班
    results.append(("每日排班", validate_daily_schedule()))
    
    # 验证周排班
    results.append(("周排班", validate_weekly_schedule()))
    
    # 验证JSON配置
    results.append(("JSON配置文件", validate_json_config()))
    
    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"\n  {name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有验证通过！")
    else:
        print("⚠️  部分验证失败，请检查")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
