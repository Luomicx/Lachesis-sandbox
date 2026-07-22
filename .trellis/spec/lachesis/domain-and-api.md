# 领域与 API 规格

## 实体

- `CareerCase`：用户案例和已确认基线。
- `Evidence`：用户资料、审核官方数据、模型假设或模拟结果。
- `Path`：工作、Offer、读研、回退；带真实/假设可信度。
- `ScenarioVersion`：路径和干预形成的不可变版本。
- `WorldRun`：场景、随机种子、运行档位、快照、事件和指标。
- `ReportSnapshot`：输入、证据、规则、目录和世界版本的不可变报告。

## 状态机

```text
draft -> intake -> confirmed -> queued -> running -> aggregated -> reported
                                      \-> failed / cancelled
```

## 最小 API

```text
POST /cases
POST /cases/{id}/documents
POST /cases/{id}/intake/messages
POST /cases/{id}/confirm
POST /cases/{id}/paths
POST /scenarios
POST /scenarios/{id}/runs
GET  /scenarios/{id}/comparison
POST /scenarios/{id}/interventions
GET  /world-runs/{id}/timeline
POST /world-runs/{id}/dialogue
POST /reports/{id}/snapshots
GET  /reports/{id}/export.pdf
```

运行状态必须返回完成世界数、总数、失败种子、数据版本和规则版本。

## Scenario: Local Deterministic Backend Vertical Slice

### 1. Scope / Trigger

- Trigger: implement the first runnable Lachesis backend without external knowledge-base, LLM, or Mesa/SimPy services.
- Scope: case confirmation, path creation, immutable scenario snapshots, synchronous deterministic batches, comparison aggregates, and world timelines backed by local JSON/JSONL artifacts.

### 2. Signatures

```text
POST /api/cases
POST /api/cases/{case_id}/confirm
POST /api/cases/{case_id}/paths
POST /api/scenarios
POST /api/scenarios/{scenario_id}/runs
GET  /api/scenarios/{scenario_id}/comparison?batch_id={batch_id}
GET  /api/world-runs/{world_id}/timeline
GET  /health
```

### 3. Contracts

- `POST /api/cases` accepts `{name, baseline}`. `baseline` must contain school, major, graduation year, GPA/rank, non-empty skills, target city, non-negative budget, family support, constraints, and long-term goal.
- A case starts as `intake`; `POST /confirm` changes it to `confirmed`. Paths and scenarios are rejected before confirmation.
- A case has at most four paths. Path type is `graduate_school` or `offer`. Offer confidence is `real` or `hypothetical`; real Offers use `user_fact`, while hypothetical Offers use `model_assumption`.
- Runs accept only `run_mode` `quick`/`standard`/`deep` (10/20/50 seeds) and `horizon_years` 1/3/5. Aggregates and world metrics use exactly one `simulation_result` source label.
- Every scenario saves an input snapshot. The deterministic seed derives from semantic baseline and path fields, never random IDs or timestamps.

### 4. Validation & Error Matrix

| Condition | HTTP | Error code |
| --- | ---: | --- |
| Body is not a JSON object or required field is invalid | 400 | `validation_error` |
| Case, scenario, batch, or world does not exist | 404 | `not_found` |
| Path/scenario requested before case confirmation | 409 | `invalid_state` |
| Stored artifact cannot be decoded | 500 | `storage_error` |

Errors are `{ "error": { "code", "message", "details"? } }`; internal tracebacks and sensitive baseline data must never be returned.

### 5. Good / Base / Bad Cases

- Good: confirm a complete case, create a graduate-school and hypothetical Offer path, run quick mode, then retrieve a two-path distribution and one world timeline.
- Base: repeat a batch for the same scenario; aggregate dimensions remain identical while the batch and world artifact IDs are new.
- Bad: create a path for an intake case, submit an incomplete baseline, or ask for a comparison without `batch_id`; each fails with an explicit API error.

### 6. Tests Required

- Integration test the complete case -> confirm -> paths -> scenario -> run -> comparison -> timeline flow.
- Assert quick mode produces 10 worlds per selected path and no failed seeds.
- Assert identical semantic scenarios generate equal metric distributions.
- Assert real and hypothetical Offers expose distinct provenance labels.
- Assert incomplete baseline input and unconfirmed-case path creation return the documented error codes.

### 7. Wrong vs Correct

#### Wrong

```python
seed = f"{scenario_id}:{path_id}:{created_at}"
```

Random identifiers and timestamps make equivalent scenario inputs produce different results.

#### Correct

```python
fingerprint = sha256(canonical_baseline_and_paths).hexdigest()
seed = f"{fingerprint}:{path_title}:{seed_number}:{horizon_years}"
```

The simulation remains reproducible for equal semantic inputs, rule versions, and seed numbers while artifact IDs remain safely unique.
