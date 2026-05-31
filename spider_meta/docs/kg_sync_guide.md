# 知识图谱数据同步指南

## 概述

本文档说明如何将知识图谱数据导入Meta-Agent的向量检索系统。

## 数据格式

### JSON Lines格式

数据源应为 `.jsonl` 文件，每行一个JSON对象：

```json
{"subject": "用户", "predicate": "拥有", "object": "账户"}
{"subject": "账户", "predicate": "包含", "object": "余额"}
{"subject": "订单", "predicate": "属于", "object": "用户"}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| subject | string | 是 | 主体实体 |
| predicate | string | 是 | 关系谓词 |
| object | string | 是 | 客体实体 |

## 使用方法

### 命令行导出

```python
from src.utils.kg_export_to_vector import KGExporter

exporter = KGExporter()
count = exporter.export_from_source("./knowledge_data/")
print(f"Exported {count} documents")
```

### 程序化导出

```python
triples = [
    {"subject": "产品", "predicate": "属于", "object": "类别"},
    {"subject": "类别", "predicate": "包含", "object": "产品"},
]
exporter = KGExporter()
count = exporter.export_from_triples(triples)
```

## 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| kg_collection_name | knowledge_graph | ChromaDB集合名称 |
| kg_top_k | 5 | 检索返回条数 |

## 批量导入建议

- 建议批量大小：100条/批
- 大文件自动分批写入
- 支持递归扫描子目录

## 注意事项

1. ChromaDB必须已安装
2. 数据目录需要读写权限
3. 重复导入会创建重复文档（按ID去重）
