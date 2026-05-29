# 规则三：技能开发与生命周期管理

> 适用对象：所有技能开发者 (Skill Developers)、提示词工程师  
> 核心目标：保证10大核心技能的代码质量、可维护性及监控可追溯性。

---

## 1. 技能开发标准

### 1.1 接口契约
所有技能（Skill）**必须**实现统一的 `SkillInterface`，包含三个抽象方法：

```python
from abc import ABC, abstractmethod
from typing import Any, Dict

class SkillInterface(ABC):
    """技能接口契约 - 所有技能必须实现"""
    
    @abstractmethod
    def validate_input(self, params: Dict[str, Any]) -> bool:
        """输入校验：验证参数完整性、类型、边界条件"""
        ...
    
    @abstractmethod
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """执行核心逻辑"""
        ...
    
    @abstractmethod
    def format_output(self, result: Dict[str, Any]) -> str:
        """输出格式化：将结果转化为可展示的格式"""
        ...
```

### 1.2 提示词工程
- **必须**包含 `System Prompt`（角色定义）和 `Few-shot Examples`（示例）
- **严禁**在代码中拼接用户输入与提示词
- **必须**使用 LangChain 的 `PromptTemplate` 实现模板化

```python
# ✅ 正确方式：使用 PromptTemplate
from langchain.prompts import PromptTemplate

prompt = PromptTemplate(
    input_variables=["user_query", "context"],
    template="""你是一个代码审查专家。
    
上下文：{context}
用户需求：{user_query}

请提供详细的代码审查报告。"""
)

# ❌ 错误方式：字符串拼接
# prompt = f"你是一个代码审查专家。用户需求：{user_input}"  # 禁止！
```

### 1.3 工具调用规范
- 使用 `@tool` 装饰器注册工具
- **必须**严格定义 `args_schema`（参数 Schema）
- 确保 LLM 能正确解析参数

---

## 2. 版本与依赖控制

### 2.1 依赖锁定
- `requirements.txt` 中**必须**锁定 LangChain 及相关库的版本
- 防止因版本更新导致的 API 不兼容

```
langchain==0.1.0
langchain-community==0.0.10
chromadb==0.4.22
qdrant-client==1.9.0
pymilvus==2.3.0
```

### 2.2 向后兼容
- 修改现有 Skill 时，必须保留旧版接口至少 **2个版本周期**
- 通过 `DeprecationWarning` 提示调用者迁移
- 废弃接口在2个版本后删除

---

## 3. 监控与日志审计

### 3.1 Trace ID 透传
- 从用户请求进入开始，**必须**生成唯一的 `trace_id`
- `trace_id` 贯穿所有19个 Agent 的日志
- 格式：`{timestamp_ms}-{agent_id}-{random_hex}`

### 3.2 关键指标埋点
每个技能调用必须埋点以下指标：

| 指标 | 说明 | 告警阈值 |
|------|------|----------|
| `Skill_Latency` | 技能执行耗时 | > 30秒 |
| `Token_Usage` | 输入/输出Token数 | 用于成本核算 |
| `Error_Rate` | 技能调用失败率 | > 5% 自动告警 |

---

## 4. 代码实现要求

| 检查项 | 达标标准 | 负责人 |
|--------|----------|--------|
| 技能接口 | 实现 SkillInterface，有单元测试 | Skill Developer |
| 提示词 | 使用 PromptTemplate，无字符串拼接 | Prompt Engineer |
| 工具注册 | @tool + args_schema 定义 | Skill Developer |
| 依赖锁定 | requirements.txt 锁定版本 | DevOps |
| 日志追踪 | 日志包含 trace_id，可关联全流程 | All Agents |
| 指标埋点 | Latency/Token/Error 全覆盖 | System Manager |