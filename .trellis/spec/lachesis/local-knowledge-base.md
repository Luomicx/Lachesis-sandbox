# 本地知识库与 RAG 规格

知识库必须经 provider-neutral `knowledge_base` 门面访问。默认实现为
无需网络或第三方依赖的本地文件系统 provider；
`backend/app/services/zep_adapter/` 仅可作为未来可选 provider 的参考，
不得成为应用启动或 career 服务的直接依赖。

## 基础设施

- 默认：本地文件系统，用于保存每个案例独立的 collection namespace。
- 可选的未来 provider：Neo4j 用于节点、关系与图谱查询；Qdrant 用于
  向量索引与语义检索；受信任 embedding 服务用于向量生成。
- 默认 provider 之外的基础设施必须显式配置，且不能成为已有案例、路径
  或仿真 API 的运行前提。

## 健康契约

- `/health` 必须保留后端的顶层健康字段，并增加 `knowledge_base` 对象。
- `knowledge_base` 对象必须包含 `provider`、`status` 与
  `case_isolation`。可安全返回简短的 `message`，但不得暴露本地绝对路径、
  凭据或内部异常详情。
- `status` 仅使用：`ready`（可使用）、`unavailable`（已禁用或依赖不可用）、
  `invalid`（配置或 provider 无效）。无效或不可用状态不得让 Flask
  应用启动失败。
- `case_isolation` 仅在当前 provider 可创建隔离 collection 时为 `true`；
  `unavailable` 与 `invalid` 状态必须返回 `false`。

## 隔离规则

- 每个案例独立 collection/namespace；默认文件系统 provider 为每个案例
  创建独立目录。
- 文件系统 collection 只接受后端生成的 `case_<12 hex characters>` 标识，
  并且必须拒绝路径分隔符、路径穿越和符号链接目录。
- 用户上传数据绝不成为全局默认数据。
- 官方数据须人工审核、带官网链接、发布日期、适用年份和版本，才可进入 catalog。
- 世界角色只读取派生属性和已发生事件，不读取原始附件、预算或家庭描述。

## 门面契约

```text
health -> create_collection
future: index_documents -> search
future: upsert_entities -> upsert_relations -> get_graph
future: append_events -> delete_collection
```

只有 `health` 与 `create_collection` 属于当前边界切片。文档摄入、检索、
图谱写入与事件追加必须在后续任务中经同一门面扩展，不能直接导入 provider
类型。任何影响量化结果的检索证据必须可回溯到来源和版本；缺少合格数据时
返回 `insufficient_data`。

## Scenario: Local Knowledge-Base Health Boundary

### 1. Scope / Trigger

- Trigger: the Flask backend needs a local knowledge-base boundary before
  document ingestion and external retrieval providers are introduced.
- Scope: configure a dependency-free filesystem provider, register it through
  `app.extensions`, report its state from `/health`, and reserve isolated
  collection directories for generated career-case IDs.

### 2. Signatures

```text
GET /health
create_knowledge_base(configuration) -> KnowledgeBase
KnowledgeBase.health() -> KnowledgeBaseHealth
KnowledgeBase.create_collection(case_id) -> Path
```

### 3. Contracts

- `LACHESIS_KNOWLEDGE_BASE_ENABLED` defaults to `true`.
- `LACHESIS_KNOWLEDGE_BASE_PROVIDER` defaults to `filesystem`; unsupported
  values do not prevent application startup.
- `LACHESIS_KNOWLEDGE_BASE_DIR` is optional; when absent, the root is
  `${LACHESIS_DATA_DIR}/knowledge-base`.
- `/health` retains `status`, `service`, and `version`, and adds:

  ```json
  {
    "knowledge_base": {
      "provider": "filesystem",
      "status": "ready",
      "case_isolation": true
    }
  }
  ```

- The filesystem provider accepts only generated IDs matching
  `case_<12 lowercase hexadecimal characters>`. It returns a direct child of
  its resolved root and rejects symbolic-link collections.

### 4. Validation & Error Matrix

| Condition | `/health` response | `create_collection` behavior |
| --- | --- | --- |
| Enabled `filesystem` root is usable | `ready`, `case_isolation: true` | Creates or returns the case directory. |
| Provider is disabled or filesystem root cannot be used | `unavailable`, `case_isolation: false` | Raises `RuntimeError`; no fallback provider. |
| Provider name or filesystem root configuration is invalid | `invalid`, `case_isolation: false` | Raises `RuntimeError`; no fallback provider. |
| Case ID has a path separator, invalid format, or collection is a symlink | Existing health state | Raises `ValueError`; no path outside the root is used. |

### 5. Good / Base / Bad Cases

- Good: default configuration reports `filesystem` as `ready`; two generated
  case IDs create separate directories below the local knowledge-base root.
- Base: existing career API flow runs with the default provider without any
  external service, embedding model, or network request.
- Bad: an unsupported provider or an unusable filesystem path is visible as a
  structured non-ready state rather than causing Flask startup to fail;
  `../case_...` and Windows backslash paths are rejected.

### 6. Tests Required

- Request `/health` with default configuration and assert its existing top-level
  fields plus ready filesystem health information.
- Create two collections through the registered facade and assert they are
  different, direct children of the configured root.
- Assert invalid traversal-style IDs raise `ValueError`.
- Assert disabled configuration and an unusable filesystem path return
  `unavailable` with `case_isolation: false`.
- Assert an unknown provider returns `invalid` with `case_isolation: false`.
- Run the complete career API suite to prove no external dependency or career
  service coupling was introduced.

### 7. Wrong vs Correct

#### Wrong

```python
collection_directory = Path(data_directory) / case_id
collection_directory.mkdir(parents=True, exist_ok=True)
```

This lets a future caller turn a path-like ID or a symbolic link into storage
outside the intended case root.

#### Correct

```python
validated_case_id = validate_generated_case_id(case_id)
collection_directory = resolved_root_directory / validated_case_id
reject_symbolic_links_and_paths_outside_the_root(collection_directory)
```

The facade owns the path-validation rule, so future intake and retrieval
services do not need provider-specific filesystem safety logic.
