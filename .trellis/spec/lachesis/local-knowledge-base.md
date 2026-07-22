# 本地知识库与 RAG 规格

使用 `backend/app/services/zep_adapter/` 作为唯一图谱和检索实现。

## 基础设施

- Neo4j：节点、关系、图谱查询和关系网络。
- Qdrant：向量索引与语义检索。
- sentence-transformers 或受信任 embedding 服务：向量生成。

## 隔离规则

- 每个案例独立 collection/namespace。
- 用户上传数据绝不成为全局默认数据。
- 官方数据须人工审核、带官网链接、发布日期、适用年份和版本，才可进入 catalog。
- 世界角色只读取派生属性和已发生事件，不读取原始附件、预算或家庭描述。

## 适配器契约

```text
create_collection -> index_documents -> search
upsert_entities -> upsert_relations -> get_graph
append_events -> delete_collection
```

任何影响量化结果的检索证据必须可回溯到来源和版本；缺少合格数据时返回 `insufficient_data`。
