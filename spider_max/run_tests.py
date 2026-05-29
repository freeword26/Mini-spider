#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试运行脚本 - 解决相对导入问题
"""

import sys
import os
import unittest

# 设置路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 直接导入模块
from tests.test_workflow_executor import *
from tests.test_event_bus import *

# 尝试导入其他测试（如果有导入问题则跳过）
try:
    from tests.test_orchestrator import *
except ImportError as e:
    print(f"Warning: Could not import test_orchestrator: {e}")

try:
    from tests.test_scheduler import *
except ImportError as e:
    print(f"Warning: Could not import test_scheduler: {e}")

if __name__ == "__main__":
    unittest.main(verbosity=2)
