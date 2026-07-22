# Lachesis 数据模型与 API

## 1. 数据实体

| 实体 | 关键字段 | 说明 |
| --- | --- | --- |
| Case | id, owner_id, device_id, status, baseline_version | 一个用户的预演案例，首版绑定当前设备 |
| Profile | education, gpa_or_rank, experience, skills, budget, family_support, preferences, constraints | 个人基线，首次运行前必须完整确认，不作为公开图谱数据 |
| Goal | target_roles, horizons, metric_weights, hard_constraints | 用户定义的目标与不可妥协项 |
| Path | kind, evidence_class, decisions, fallback_policy, initial_conditions | 工作、读研或混合路径；evidence_class 区分真实 Offer 与假设路径；每个案例最多 4 条 |
| ScenarioVersion | parent_id, interventions, assumption_set_id, engine_version | 可复现的不可变情景版本 |
| WorldRun | scenario_id, seed, run_mode, status, snapshot_uri, outcome | 一次具体世界运行，run_mode 为 fast/default/deep |
| Event | world_run_id, month, type, actor, payload, provenance | 领域事件的事实台账 |
| RoleContext | world_run_id, role_id, derived_attributes, policy_version | 仅含最小化派生属性的世界角色上下文 |
| Evidence | source_type, source_ref, published_at, applicable_year, uploader, review_status, confidence | 用户输入、用户上传资料、经人工审核的官方数据、默认值或模型假设 |
| Report | scenario_set, metrics, comparisons, citations, provenance_label, immutable_snapshot | 聚合结果及其不可变快照；每项结论只有一个来源标签 |

## 2. 路径示例

```json
{
  "id": "path_grad_key_cs",
  "kind": "graduate_study",
  "start_month": 0,
  "duration_months": 36,
  "education": {
    "target_tier": "key",
    "major_track": "computer_science",
    "prep_months": 10,
    "tuition_per_year": 18000,
    "living_cost_per_month": 3500,
    "admission_probability": {"low": 0.28, "mid": 0.45, "high": 0.60}
  },
  "fallback_policy": {
    "on_admission_failure": "job_search",
    "max_retry_count": 0
  }
}
```

## 3. 事件示例

```json
{
  "id": "evt_2028_04_001",
  "world_run_id": "run_a_seed_17",
  "month": 16,
  "type": "internship_offer_received",
  "actor": "person",
  "payload": {
    "organization_tier": "growth_stage",
    "role_family": "ml_engineering",
    "compensation": 8500,
    "source": "market_rule_v3"
  },
  "provenance": {
    "rule_version": "career-rules-0.3.0",
    "evidence_ids": ["evidence_market_2027_q4"],
    "random_seed": 17
  }
}
```

## 4. API 设计

所有写入接口需要身份认证、案例所有权校验和审计日志。所有异步任务返回 `task_id`；查询接口支持按版本和世界筛选。资料解析后的个人档案必须由建模官预填、追问补全并获得用户一次性确认，才允许创建首个情景。

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| POST | `/api/cases` | 创建案例 |
| POST | `/api/cases/{caseId}/documents` | 上传 PDF、DOCX、图片或结构化手动资料 |
| POST | `/api/cases/{caseId}/intake/messages` | 与生涯建模官对话并更新待确认档案 |
| GET/PATCH | `/api/cases/{caseId}` | 读取或更新草稿基线 |
| POST | `/api/cases/{caseId}/paths` | 创建路径 |
| POST | `/api/cases/{caseId}/scenarios` | 从路径与假设创建情景版本 |
| POST | `/api/scenarios/{id}/runs` | 启动批量世界运行 |
| GET | `/api/scenarios/{id}/comparison` | 获取分布、敏感性与对比 |
| GET | `/api/world-runs/{id}/timeline` | 获取时间线和快照 |
| POST | `/api/scenarios/{id}/interventions` | 注入变量并创建子版本 |
| POST | `/api/world-runs/{id}/dialogue` | 与当前世界角色对话 |
| POST | `/api/evidence` | 用户或运营人员上传公开数据及其官网来源 |
| POST | `/api/reports/{id}/snapshots` | 保存包含输入、证据、规则和运行范围的不可变报告快照 |
| GET | `/api/reports/{id}/export.pdf` | 导出自动剔除敏感原始资料的 PDF 报告 |
| GET | `/api/reports/{id}` | 读取带引用的报告 |

## 5. 任务状态

```text
draft -> validated -> queued -> running -> aggregating -> completed
                               \-> failed / cancelled
```

运行状态单独于案例状态存储。失败必须保存失败原因、引擎版本和最后成功快照，允许从快照重试。

## 6. 持久化策略

- 关系型数据库：用户、案例、版本、权限、路径、假设、任务、汇总结果和证据审核状态。
- 对象存储：原始附件、运行事件 JSONL、快照、导出报告和 LLM 缓存。
- 向量/图谱存储：仅保存经用户授权的个人资料摘要、可检索的外部证据和规则解释；不要将原始简历无差别上传至第三方服务。
- 队列与 Worker：批量世界运行与报告生成必须脱离 Web 进程。

## 7. 安全与数据生命周期

- PII 字段列级加密，密钥与应用数据分离。
- 默认私有，不提供公共案例链接；共享须指定权限和有效期。
- 支持导出、软删除和物理删除任务；物理删除需覆盖对象存储、缓存和检索索引。
- 在日志中使用内部 ID，不记录完整简历、联系方式或敏感提示词。
- 外部数据与用户主张须标注来源、时间和适用范围；未知项不得伪造出处。
- 用户上传的公开数据按案例隔离；只有运营人员审核通过且带官网来源的数据可以进入全局默认数据集。
- 首版不具备实时全网爬取能力；带官网来源的运营上传数据仍须经过人工审核才可进入全局默认数据集。
- 网络检索内容初始状态必须为 `pending_review`；缺少来源链接、发布日期或适用年份的记录不得参与结果计算。
- 首版账号、案例、上传文件和报告均与注册设备绑定；跨设备查询、同步和恢复请求必须被拒绝，设备丢失或更换后的数据恢复请求同样被拒绝。
- PDF 导出只能使用报告快照中的聚合结论、生命线和证据摘要，不能包含原始附件、预算、家庭支持或其他敏感输入。
- 个人资料的模型服务必须来自平台受信任配置，并声明不将请求数据用于训练；未通过配置校验的第三方模型端点不得接收敏感输入。
- 所有运行均异步执行，任务状态须包含 completed_worlds、total_worlds、data_version、rule_version 和 failed_seeds；服务不承诺逐事件实时流或秒级完成。
- 世界角色上下文必须单独存储并经过字段白名单；其内容不得包含原始附件、成绩单原文、具体家庭描述或其他敏感资料原文。
- 所有可影响指标的 LLM 事件必须关联 rule_id、input_id 或 evidence_id；缺失关联时仅可存储为叙事事件。
