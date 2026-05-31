# Kilo 配置参考

## 模型配置

| 用途 | 模型 |
|------|------|
| 默认模型 | kilo/poolside/laguna-xs.2:free |
| 小模型 | kilo/kilo-auto/free |
| 子Agent | kilo/openrouter/owl-alpha |
| code | deepseek/deepseek-v4-pro |
| 其他Agent | kilo/stepfun/step-3.5-flash:free |

## Agent 列表

| Agent | 模式 | 主要权限 |
|-------|------|----------|
| plan | primary | 只读+计划文件编辑 |
| debug | primary | 只读 |
| orchestrator | primary | - |
| ask | primary | - |
| code | primary | 全权限 |
| architect | primary | 只读+计划文件 |
| code-reviewer | primary | 只读 |
| code-simplifier | primary | 全权限 |
| code-skeptic | primary | 只读+md编辑 |
| docs-specialist | primary | 只读+文档编辑 |
| frontend-specialist | primary | 只读+前端文件编辑 |
| test-engineer | primary | 只读+测试文件编辑 |

## 实验特性

- batch_tool: true
- codebase_search: true
- semantic_indexing: true
- agent_manager_tool: true
- openTelemetry: true
- continue_loop_on_deny: true
- disable_paste_summary: true

## 索引配置

- 启用: true
- 提供商: voyage
- 模型: mistralai/mistral-embed-2312
