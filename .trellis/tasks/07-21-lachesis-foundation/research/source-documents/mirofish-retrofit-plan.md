# Lachesis 基于 MiroFish 的改造计划

## 1. 改造结论

不应从零创建 Lachesis，也不应把“考研/工作”硬塞进 Twitter/Reddit 模拟。正确路径是保留 MiroFish 的项目工作流、资料处理、异步任务、Agent 报告、图谱展示和交互骨架，替换其云端 Zep 依赖与 OASIS 社交平台领域内核。

```text
保留的 MiroFish 外壳
  资料导入 -> 世界准备 -> 异步运行 -> 报告 -> 对话/分叉

替换的领域内核
  Zep Cloud + Twitter/Reddit/OASIS
  -> Local Knowledge Base + CareerWorld(Mesa + SimPy)
```

最终目标不是维护两套产品，而是在当前仓库中引入一个明确的 `career` 领域模块，使原有 MiroFish 的通用能力继续可用。

## 2. 当前架构基线

当前项目由 Vue 3 前端和 Flask 后端组成。后端以 `graph`、`simulation`、`report` 三个 Blueprint 组织 API；项目、模拟和报告均已有本地 JSON/JSONL 持久化与异步任务能力。

```text
Vue 3 + D3
  -> Flask API: graph / simulation / report
       -> 项目与文件管理、任务管理、LLM 调用
       -> Zep Cloud: 图谱、实体、检索、记忆
       -> OASIS: Twitter/Reddit 双平台子进程
       -> ReportAgent: 工具调用、报告、追问
```

当前关键问题是：`Zep` 和 `Twitter/Reddit` 的平台语义散落在 API、服务、运行器和前端文案中。因此改造必须先建立抽象边界，再切换实现，不能直接替换单个 SDK 调用。

## 3. 代码复用矩阵

| 当前模块 | 处置 | Lachesis 用途 | 改造方式 |
| --- | --- | --- | --- |
| `backend/app/models/project.py` | 复用并演进 | 案例、上传文件、状态和元数据 | 将 `Project` 演进为 `CareerCase`，保留目录与版本化模式 |
| `backend/app/utils/file_parser.py` | 直接复用 | PDF、DOCX、图片资料的文本提取 | 扩展 DOCX/图片 OCR，保留多文件提取接口 |
| `backend/app/services/text_processor.py` | 直接复用 | RAG 分块与资料摘要 | 让分块元数据携带案例、来源和敏感级别 |
| `backend/app/models/task.py` 与任务 API | 直接复用 | 资料解析、知识库构建、批量运行、报告生成 | 为任务增加 `case_id`、`scenario_id`、`run_mode` |
| `backend/app/services/report_agent.py` | 抽象后复用 | 生命线报告、依据追溯、报告对话 | 替换工具集，保留分段生成、进度、日志和快照 |
| `backend/app/services/llm_client.py` | 直接复用 | 建模官、角色叙事、报告 | 增加受信任模型端点与敏感数据策略 |
| `frontend/src/views/*` 与 Router | 抽象后复用 | 案例、运行、报告和未来世界页面 | 替换五步文案与数据契约，不重建应用壳 |
| `frontend/src/components/GraphPanel.vue` | 直接复用 | 关系网络、路径树、证据关系图 | 改节点/边数据，不再依赖 Zep 图谱格式 |
| `frontend/src/components/Step4Report.vue` | 抽象后复用 | 模拟报告及其来源标签 | 删除“预测推荐”语义，增加事实/数据/假设/模拟标签 |
| `backend/app/services/simulation_runner.py` | 保留运行器概念，重写实现 | CareerWorld 的异步批次运行、快照、进度 | 将平台/动作日志改为 world/事件日志 |
| `backend/app/services/simulation_ipc.py` | 抽象后复用 | Worker 控制、停止、状态检查 | 增加快照/取消/重试，删除采访和平台参数 |
| `backend/app/services/simulation_manager.py` | 重写领域实现 | 情景创建、路径配置、世界准备 | 新建 `career_simulation_manager.py`，不继续扩展 OASIS 逻辑 |
| `backend/app/services/oasis_profile_generator.py` | 替换 | 个人分身与关系角色生成 | 新建 `career_role_generator.py`，输出最小化派生属性 |
| `backend/scripts/run_*_simulation.py` | 替换 | Mesa + SimPy 运行入口 | 新建单一 `run_career_world.py` |
| `zep_*` 服务与 `graph_builder.py` | 抽象后替换 | 本地知识库、检索、关系网络、模拟记忆 | 通过 `KnowledgeBaseAdapter` 迁移，移除 Cloud 强依赖 |

## 4. 目标模块结构

```text
backend/app/
  api/
    career_case.py              # 案例、资料、建模官
    career_scenario.py          # 路径、情景、分叉
    career_world.py             # 运行、生命线、关系、对话
    report.py                   # 保留，增加 career report 工具
  models/
    career_case.py
    career_scenario.py
    career_world.py
    evidence.py
  services/
    knowledge_base/
      adapter.py                # 新接口，屏蔽 Zep/本地实现差异
      local_adapter.py          # 你后续提供的 zep_adapter 适配入口
      evidence_registry.py
    career_intake_agent.py
    career_role_generator.py
    career_simulation_manager.py
    career_world_runner.py
    career_report_tools.py
    dataset_catalog.py
  workers/
    run_career_world.py
  data/
    career_catalog/             # 已审核的 20 项目、6 城市、年度版本
```

新模块不能导入 `zep_cloud`、`camel_oasis` 或带有 Twitter/Reddit 平台名的类型。旧模块暂时保留，仅作为原产品兼容层，避免在迁移中破坏现有能力。

## 5. 知识库本地化计划

### 5.1 先定义稳定接口

在引入你后续上传的 `zep_adapter` 前，先定义本地知识库契约。当前业务代码只能依赖该契约，禁止直接使用 Zep SDK：

```python
class KnowledgeBaseAdapter(Protocol):
    def create_collection(self, case_id: str, name: str) -> str: ...
    def index_documents(self, collection_id: str, chunks: list[DocumentChunk]) -> IndexResult: ...
    def search(self, collection_id: str, query: str, limit: int = 10) -> list[SearchHit]: ...
    def upsert_entities(self, collection_id: str, entities: list[Entity]) -> None: ...
    def upsert_relations(self, collection_id: str, relations: list[Relation]) -> None: ...
    def get_graph(self, collection_id: str) -> GraphData: ...
    def append_events(self, collection_id: str, events: list[CareerEvent]) -> None: ...
    def delete_collection(self, collection_id: str) -> None: ...
```

`zep_adapter` 上传后应适配到该接口，而不是让上层业务重新耦合其私有 API。

### 5.2 数据隔离与来源

- 每个案例一个本地 collection/namespace；用户上传资料绝不进入全局目录。
- 运营审核后的官方数据按年度 catalog 独立索引；运行记录引用 catalog 版本。
- 角色只能读取 `RoleContext` 中的派生属性和经过授权的世界事件。
- 原始附件、预算、家庭支持和成绩单不进入角色检索上下文。

### 5.3 当前 Zep 替换顺序

1. `graph_builder.py`：改为调用 `KnowledgeBaseAdapter.index_documents` 与实体/关系写入。
2. `zep_entity_reader.py`：改为 `KnowledgeBaseAdapter.get_graph` 后进行本地过滤。
3. `zep_tools.py`：拆成 `career_report_tools.py`，改用本地搜索、事件、统计与关系查询。
4. `zep_graph_memory_updater.py`：改为追加 `CareerEvent`，不再更新 Cloud 图谱。
5. API 中的 `Config.ZEP_API_KEY` 检查：先改为 `Config.KNOWLEDGE_BASE_MODE`；待验证后删除 Zep Cloud 强制门禁。

## 6. CareerWorld 替换计划

### 6.1 保留运行生命周期

保留当前 `SimulationRunner` 的可观察性设计：创建、准备、运行、停止、完成、失败、进度轮询、日志、历史和报告关联。将数据语义替换如下：

| 当前语义 | 新语义 |
| --- | --- |
| `simulation_id` | `world_batch_id` |
| Twitter/Reddit 平台 | 路径与情景版本 |
| `AgentAction` | `CareerEvent` |
| 平台轮次/小时 | 月度或季度时间步 |
| actions JSONL | events JSONL |
| 平台数据库 | 世界快照与指标聚合 |
| interview IPC | 运行完成后的只读世界对话 |

### 6.2 Mesa + SimPy 职责划分

- Mesa：`CareerWorld`、个人分身、关系角色、学校、组织、市场 Agent，以及重复随机世界。
- SimPy：备考、录取、读研、求职、就业、实习、晋升、现金流和冲击的离散事件过程。
- 规则引擎：资格、时间、预算、容量、概率和因果约束；拥有所有状态写入权。
- LLM：建模官、角色叙事与报告解释；任何影响指标的提议事件须通过规则校验并关联规则、输入或证据。

### 6.3 新运行产物

```text
uploads/career_cases/{case_id}/
  profile.json
  scenarios/{scenario_id}/
    input_snapshot.json
    evidence_versions.json
    runs/{seed}/
      events.jsonl
      snapshots.jsonl
      metrics.json
      role_contexts.json
    aggregate.json
    report_snapshot.json
```

保留当前项目将状态写入本地文件的可用性，但新文件必须不可变版本化；不要继续复用 `twitter/`、`reddit/` 和平台动作目录。

## 7. 前端改造计划

| 当前页面/组件 | 改造后页面/组件 | 复用策略 |
| --- | --- | --- |
| Home / HistoryDatabase | 案例列表 | 保留历史列表与状态展示，改为案例/报告快照 |
| Process / Step1GraphBuild | 生涯建模 | 保留文件上传、任务进度和图谱区域，加入建模官追问与必填确认 |
| Step2EnvSetup | 路径与数据配置 | 用 Offer、冲刺/匹配/保底、catalog 版本替换平台配置 |
| SimulationRunView / Step3Simulation | 世界批量运行 | 保留进度、停止、日志，显示 10/20/50 个世界与失败种子 |
| ReportView / Step4Report | 人生预演报告 | 保留章节流与日志，增加免责声明、来源标签、数据不足状态 |
| InteractionView / Step5Interaction | 生命线与只读角色对话 | 保留分屏/工作台模式，左侧复用 GraphPanel 作为关系网络 |

第一版不实现 2.5D、角色移动或实时动画。重点是宏观路径树、前 12 个月月度生命线、之后季度生命线、关系网络、世界选择和分叉差分。

## 8. 分期实施与验收

### Phase 0：隔离边界（3-5 天）

- 新建 `KnowledgeBaseAdapter`、Career 数据模型和配置开关。
- 将 Zep 访问集中到适配层，不改原业务行为。
- 建立 `CareerEvent`、`ScenarioVersion`、`RoleContext` 的 JSON Schema。

验收：现有 MiroFish 仍可启动；新 Career 模块不直接导入 `zep_cloud` 或 OASIS。

### Phase 1：本地知识库与建模官（1-2 周）

- 接入你提供的 `zep_adapter` 本地实现并适配接口。
- 复用文件解析、分块、任务管理和 LLM 客户端。
- 实现资料提取、追问、必填确认、来源登记与资料隔离。

验收：可导入资料、完成必填档案、建立本地 collection 并检索到带来源的内容；不需要 `ZEP_API_KEY`。

### Phase 2：路径、目录与规则（1-2 周）

- 实现真实/假设 Offer、读研冲刺/匹配/保底、回退路径和最多四路径比较。
- 实现运营人员配置的 20 项目/6 城市 catalog、人工审核与年度版本。
- 实现数据不足状态与四类报告来源标签。

验收：目录外对象不会产生量化概率；假设 Offer 始终显示为假设路径。

### Phase 3：Mesa + SimPy 世界运行（2-3 周）

- 重写模拟管理器、运行器与 worker，保留任务状态/日志/停止/重试框架。
- 实现 1/3/5 年、10/20/50 世界、事件日志、快照和聚合。
- 实现教育、工作、现金流、关系和市场冲击的最小规则集。

验收：相同种子和版本可复现；每个事件可回溯到规则、输入或证据；失败种子可定位。

### Phase 4：报告、关系网络与分叉（1-2 周）

- 用 Career 工具替换 ReportAgent 的 Zep 工具。
- 复用 GraphPanel、报告视图与交互工作台。
- 实现只读角色对话、保存快照、脱敏 PDF、可控前因分叉。

验收：没有总分、排名或推荐按钮；角色不可改写世界；旧快照在当前设备可回放。

## 9. 不可违反的迁移规则

1. 不在业务层直接调用 `zep_cloud`；所有知识库能力经适配器访问。
2. 不在 Career 模块复用 Twitter/Reddit、帖子、评论、点赞等平台类型。
3. 不让 LLM 直接写录取、升职、收入或指标结果。
4. 不用用户上传的公开数据改变其他用户的默认结果。
5. 不将原始附件和敏感家庭/财务信息提供给世界角色。
6. 不在迁移前删除现有 MiroFish 模块；先并行新增，再按 API 和 UI 分阶段切换。

## 10. 首个开发切片

建议从一个端到端的最小垂直切片开始，而不是先重构所有服务：

```text
导入一份简历/成绩单
  -> 建模官补齐 GPA、预算、家庭支持
  -> 本地知识库检索资料
  -> 创建“考研匹配院校”与“假设 Offer”两条路径
  -> 运行 10 个、1 年世界
  -> 展示生命线、数据来源、数据不足与保存报告
```

该切片可验证本地 RAG、用户资料隔离、CareerWorld、报告和前端改造是否能一起成立，再扩展到 20 项目/6 城市、50 世界和更多分叉。
