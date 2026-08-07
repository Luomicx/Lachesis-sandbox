# 架构规格

```text
Vue 3 Frontend
  -> Flask API
       -> Case / Scenario / World / Report services
       -> Local Knowledge Base facade (filesystem default; optional providers)
       -> CareerWorld (Mesa + SimPy workers)
       -> Local object storage and JSONL snapshots
```

## 模块边界

- `intake`：资料解析、建模官追问、档案确认。
- `knowledge_base`：本地文档索引、来源检索、实体和关系图。
- `catalog`：运营审核的二十个项目、六个城市和年度版本。
- `careerworld`：规则、世界运行、事件、快照和指标聚合。
- `reporting`：只读取世界产物，生成带来源标签的报告。
- `frontend`：路径树、生命线、关系网络、只读角色对话和分叉。

业务模块不得直接导入 `zep_cloud`、OASIS、Twitter 或 Reddit 类型。所有知识库调用
经 `knowledge_base` 门面；默认文件系统 provider 不依赖外部服务，未来可选
provider 才可在门面之后桥接至具体适配器。

## 项目目录

```text
backend/app/{api,models,services,workers}
frontend/src/{views,components,api}
spec/
```
