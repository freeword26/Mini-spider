#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spider_max v3.0 — 一键启动
全栈项目管理与多Agent智能体协同平台
"""

import sys
import os
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR.parent) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR.parent))
os.chdir(str(SCRIPT_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        os.environ.setdefault("PYTHONIOENCODING", "utf-8")

BANNER = r"""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     Spider Max / spider_max  v3.0                               ║
║     全栈项目管理 · 多Agent协同 · OKR · DAG · 数据分析        ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""


def main():
    from spider_max.cli import cli
    if len(sys.argv) <= 1:
        sys.argv.append("--help")
    print(BANNER)
    cli(standalone_mode=False)


if __name__ == "__main__":
    main()
