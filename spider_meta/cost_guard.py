"""
spider_meta 自动成本控制 + Token 消费追踪

立项协议约束：
  - 月成本上限：¥50/天（日均 ¥1.67）
  - 本地优先：敏感数据不经过云端
  - GPU 显存 ≤3.5GB，RAM ≤24GB，CPU ≤80%

成本模型（2026-05-30 更新）：
  ┌──────────────┬────────────────────┬───────────────┐
  │ 服务商        │ 模型               │ 价格           │
  ├──────────────┼────────────────────┼───────────────┤
  │ OpenRouter    │ gpt-4o-mini        │ ¥0.11/1M tok  │
  │ OpenRouter    │ gpt-3.5-turbo      │ ¥0.075/1M tok │
  │ OpenRouter    │ claude-3-haiku     │ ¥0.02/1M tok  │
  │ 本地推理      │ llama-3 (GGUF)     │ ¥0（纯本地）    │
  │ 本地模拟      │ _simulate_llm()    │ ¥0（零成本）    │
  └──────────────┴────────────────────┴───────────────┘

降级策略（优先级从高到低）：
  1. 模拟模式（零成本）：不调用任何外部 API
  2. 本地模型（零成本）：使用 llama.cpp / Ollama 本地推理
  3. 最便宜付费模型：claude-3-haiku（¥0.02/1M tokens）
  4. 默认模型：gpt-4o-mini（¥0.11/1M tokens）
"""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger("spider_meta.cost_guard")

# ============================================================
# 定价表（每百万 tokens，单位：¥）
# ============================================================
PRICING: Dict[str, float] = {
    # OpenRouter 常用模型
    "gpt-4o":               1.80,
    "gpt-4o-mini":          0.11,
    "gpt-3.5-turbo":        0.075,
    "claude-3-haiku":       0.02,
    "claude-3-sonnet":      0.23,
    "claude-3-opus":        1.12,
    # DeepSeek
    "deepseek-chat":        0.14,
    "deepseek-reasoner":    0.55,
    # 本地推理（零成本）
    "qwen2.5:7b":           0.00,
    "qwen2.5-coder:7b":     0.00,
    "llama-3-8b":           0.00,
    "llama-3-70b":          0.00,
    "ollama/llama3":        0.00,
    "ollama/qwen2.5":      0.00,
    "ollama/qwen2.5-coder": 0.00,
    # 本地模拟（零成本）
    "simulation":           0.00,
    "_simulate_llm()":      0.00,
}

# ============================================================
# 预算配置（与 config.py HARDWARE_LIMITS 保持一致）
# ============================================================
from spider_meta.config import HARDWARE_LIMITS

MONTHLY_BUDGET_RMB  = HARDWARE_LIMITS["max_monthly_cost_rmb"]   # ¥50/月
DAILY_BUDGET_RMB    = HARDWARE_LIMITS["daily_budget_rmb"]        # ~¥1.67/天
WARNING_THRESHOLD   = 0.80   # 80% 告警
CRITICAL_THRESHOLD  = 0.95   # 95% 强制降级

# 持久化路径
DATA_DIR = Path(os.getenv("SPIDER_META_DATA", "data"))
COST_LOG_PATH      = DATA_DIR / "cost_log.json"
TOKEN_STATS_PATH   = DATA_DIR / "token_stats.json"
BUDGET_STATE_PATH  = DATA_DIR / "budget_state.json"


@dataclass
class TokenUsage:
    """单次 API 调用的 token 用量"""
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = "unknown"
    cost_rmb: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class DailyCost:
    """当日成本汇总"""
    date: str = field(default_factory=lambda: date.today().isoformat())
    total_rmb: float = 0.0
    total_tokens: int = 0
    call_count: int = 0
    models_used: Dict[str, int] = field(default_factory=dict)
    fallback_count: int = 0  # 降级到本地/模拟的次数


class BudgetManager:
    """预算管理器：追踪消费、触发降级、生成报告"""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.daily: DailyCost = self._load_today()
        self.monthly_rmb: float = self._load_monthly()

    # ---- 持久化 ----

    def _load_today(self) -> DailyCost:
        if TOKEN_STATS_PATH.exists():
            try:
                data = json.loads(TOKEN_STATS_PATH.read_text(encoding="utf-8"))
                if data.get("date") == date.today().isoformat():
                    return DailyCost(**{k: v for k, v in data.items()
                                        if k in DailyCost.__dataclass_fields__})
            except Exception:
                pass
        return DailyCost()

    def save(self):
        TOKEN_STATS_PATH.write_text(
            json.dumps(self.daily.__dict__, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_monthly(self) -> float:
        if BUDGET_STATE_PATH.exists():
            try:
                data = json.loads(BUDGET_STATE_PATH.read_text(encoding="utf-8"))
                if data.get("month") == date.today().strftime("%Y-%m"):
                    return data.get("spent_rmb", 0.0)
            except Exception:
                pass
        return 0.0

    def save_monthly(self):
        BUDGET_STATE_PATH.write_text(
            json.dumps({
                "month": date.today().strftime("%Y-%m"),
                "spent_rmb": self.monthly_rmb,
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ---- 核心：记录一次 API 调用 ----

    def record_call(self, input_tokens: int, output_tokens: int, model: str) -> TokenUsage:
        """记录一次 API 调用，返回 TokenUsage 对象。"""
        cost = self._calc_cost(input_tokens, output_tokens, model)
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model,
            cost_rmb=cost,
        )

        # 更新日统计
        self.daily.total_rmb += cost
        self.daily.total_tokens += input_tokens + output_tokens
        self.daily.call_count += 1
        self.daily.models_used[model] = self.daily.models_used.get(model, 0) + 1

        # 更新月统计
        self.monthly_rmb += cost

        # 持久化
        self.save()
        self.save_monthly()

        # 写日志
        self._log_call(usage)

        # 触发预算检查
        self._check_budget()

        return usage

    # ---- 降级模式记录（本地/模拟） ----

    def record_fallback(self, reason: str, input_tokens: int = 0):
        """记录一次降级调用（零成本，但追踪 token 消耗）。"""
        self.daily.fallback_count += 1
        self.daily.total_tokens += input_tokens
        self.save()
        logger.info(f"[降级] {reason} | 今日降级次数: {self.daily.fallback_count}")

    # ---- 成本计算 ----

    @staticmethod
    def _calc_cost(input_tokens: int, output_tokens: int, model: str) -> float:
        price_per_million = PRICING.get(model, 0.11)  # 默认 gpt-4o-mini 价格
        total_tokens = input_tokens + output_tokens
        return round(total_tokens / 1_000_000 * price_per_million, 6)

    # ---- 预算检查 ----

    def _check_budget(self):
        daily_pct = self.daily.total_rmb / DAILY_BUDGET_RMB
        monthly_pct = self.monthly_rmb / MONTHLY_BUDGET_RMB

        if daily_pct >= CRITICAL_THRESHOLD or monthly_pct >= CRITICAL_THRESHOLD:
            logger.critical(
                f"🛑 预算超支！日: ¥{self.daily.total_rmb:.4f}/{DAILY_BUDGET_RMB:.2f} "
                f"({daily_pct:.0%}) | 月: ¥{self.monthly_rmb:.4f}/{MONTHLY_BUDGET_RMB:.0f} "
                f"({monthly_pct:.0%}) — 强制降级到模拟模式"
            )
        elif daily_pct >= WARNING_THRESHOLD or monthly_pct >= WARNING_THRESHOLD:
            logger.warning(
                f"⚠️ 预算警告！日: ¥{self.daily.total_rmb:.4f}/{DAILY_BUDGET_RMB:.2f} "
                f"({daily_pct:.0%}) | 月: ¥{self.monthly_rmb:.4f}/{MONTHLY_BUDGET_RMB:.0f} "
                f"({monthly_pct:.0%}) — 建议使用更便宜的模型或本地推理"
            )

    # ---- 日志 ----

    def _log_call(self, usage: TokenUsage):
        entry = {
            "ts": usage.timestamp,
            "model": usage.model,
            "input_tok": usage.input_tokens,
            "output_tok": usage.output_tokens,
            "cost_rmb": usage.cost_rmb,
        }
        # 追加写 JSON Lines
        with open(DATA_DIR / "cost_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # ---- 报告 ----

    def report(self) -> dict:
        return {
            "date": self.daily.date,
            "daily": {
                "spent_rmb": round(self.daily.total_rmb, 4),
                "budget_rmb": round(DAILY_BUDGET_RMB, 2),
                "pct": round(self.daily.total_rmb / DAILY_BUDGET_RMB, 4),
                "tokens": self.daily.total_tokens,
                "calls": self.daily.call_count,
                "fallbacks": self.daily.fallback_count,
                "models": self.daily.models_used,
            },
            "monthly": {
                "spent_rmb": round(self.monthly_rmb, 4),
                "budget_rmb": MONTHLY_BUDGET_RMB,
                "pct": round(self.monthly_rmb / MONTHLY_BUDGET_RMB, 4),
            },
            "status": self._status(),
        }

    def _status(self) -> str:
        daily_pct = self.daily.total_rmb / DAILY_BUDGET_RMB
        monthly_pct = self.monthly_rmb / MONTHLY_BUDGET_RMB
        if daily_pct >= CRITICAL_THRESHOLD or monthly_pct >= CRITICAL_THRESHOLD:
            return "critical"
        if daily_pct >= WARNING_THRESHOLD or monthly_pct >= WARNING_THRESHOLD:
            return "warning"
        return "ok"

    # ---- 模式决策 ----

    def resolve_mode(self, requested_model: str) -> dict:
        """
        根据预算决定使用哪种推理模式。

        返回：
          {"mode": "api"|"fallback_simulation"|"fallback_local", "model": str, "reason": str}
        """
        daily_pct = self.daily.total_rmb / DAILY_BUDGET_RMB
        monthly_pct = self.monthly_rmb / MONTHLY_BUDGET_RMB

        # 预算耗尽 → 强制模拟
        if daily_pct >= CRITICAL_THRESHOLD or monthly_pct >= CRITICAL_THRESHOLD:
            return {
                "mode": "fallback_simulation",
                "model": "simulation",
                "reason": f"预算超支（日 {daily_pct:.0%} / 月 {monthly_pct:.0%}），强制模拟模式",
            }

        # 预算警告 → 尝试用最便宜的付费模型
        if daily_pct >= WARNING_THRESHOLD or monthly_pct >= WARNING_THRESHOLD:
            return {
                "mode": "api",
                "model": "claude-3-haiku",  # ¥0.02/1M，最便宜
                "reason": f"预算预警（日 {daily_pct:.0%} / 月 {monthly_pct:.0%}），切换到最便宜模型",
            }

        # 有本地 Ollama → 优先本地推理（零成本）
        if self._ollama_available():
            return {
                "mode": "fallback_local",
                "model": "ollama/llama3",
                "reason": "本地 Ollama 可用，优先本地推理零成本",
            }

        # 正常模式：使用请求的模型
        if requested_model not in PRICING:
            logger.warning(f"未知模型 '{requested_model}'，使用默认定价 ¥0.11/1M")
        return {
            "mode": "api",
            "model": requested_model,
            "reason": "预算充足，使用请求模型",
        }

    @staticmethod
    def _ollama_available() -> bool:
        """检测本地 Ollama 是否可用。"""
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=2)
            return r.status_code == 200
        except Exception:
            return False


# ============================================================
# 全局单例
# ============================================================
budget_mgr = BudgetManager()
