# 知识图谱配置指南

## 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| kg_collection_name | string | "knowledge_graph" | ChromaDB collection名称 |
| kg_top_k | int | 5 | 召回Top-K条数 |
| enable_knowledge_retrieval | bool | True | 知识检索总开关 |
| kg_cache_size | int | 1000 | LRU缓存大小 |
| kg_retrieval_timeout | float | 2.0 | 检索超时时间（秒） |

## 启用/禁用

### 启用知识检索

设置 `enable_knowledge_retrieval: true`（默认值）。启用后，所有知识检索请求正常执行。

### 禁用知识检索

设置 `enable_knowledge_retrieval: false`。禁用后所有知识检索请求将立即返回空结果，不影响其他模块正常运行。

## 性能调优

### 缓存大小

- 增大 `kg_cache_size` 可提高缓存命中率，但会增加内存占用
- 建议值：500-2000，根据查询频率调整
- 默认值：1000

### 超时时间

- `kg_retrieval_timeout` 控制单次检索的最大等待时间
- 建议值：1.0-5.0秒
- 超时后自动降级为空结果
- 默认值：2.0秒

### Top-K

- `kg_top_k` 控制每次检索返回的最大文档数
- 增大值可提高召回率，但会增加LLM上下文长度
- 建议值：3-10
- 默认值：5

## 降级策略

当ChromaDB不可用时，KnowledgeRetriever自动降级：

1. 返回空结果
2. 记录警告日志
3. 不影响其他模块正常运行

## 配置示例

```python
# 默认配置（推荐）
kg_collection_name = "knowledge_graph"
kg_top_k = 5
enable_knowledge_retrieval = True
kg_cache_size = 1000
kg_retrieval_timeout = 2.0

# 高性能配置（高频查询场景）
kg_cache_size = 2000
kg_retrieval_timeout = 5.0
kg_top_k = 10

# 轻量配置（低资源环境）
kg_cache_size = 500
kg_retrieval_timeout = 1.0
kg_top_k = 3
```
