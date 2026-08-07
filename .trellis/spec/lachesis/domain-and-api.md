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
PATCH /cases/{id}
POST /cases/{id}/documents
GET  /cases/{id}/documents
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

- `POST /api/cases` and the case lifecycle are superseded by the
  `Case Document Intake and Draft Baselines` scenario below. That scenario
  retains the complete `{name, baseline}` request as a compatible intake flow.
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

## Scenario: Case Document Intake and Draft Baselines

### 1. Scope / Trigger

- Trigger: users need to store case-private source materials and complete their
  baseline over multiple local requests before any career path is modelled.
- Scope: raw attachment storage, safe metadata listing, draft-baseline updates,
  and confirmation-time validation. This scenario does not parse files, run
  OCR, index text, call an LLM, or change simulation inputs.

### 2. Signatures

```text
POST  /api/cases
PATCH /api/cases/{case_id}
POST  /api/cases/{case_id}/documents
GET   /api/cases/{case_id}/documents
POST  /api/cases/{case_id}/confirm
```

### 3. Contracts

- `POST /api/cases` accepts `{name}` to create a `draft` with
  `baseline: {}` and `baseline_version: 0`. The existing complete
  `{name, baseline}` request remains valid and creates an `intake` case with
  `baseline_version: 1`.
- `PATCH /api/cases/{case_id}` accepts `{baseline: {...}}`, where keys are a
  subset of the required baseline fields. It merges supplied fields for only
  `draft` and `intake` cases, increments `baseline_version` only when the
  stored baseline changes, and transitions a changed draft to `intake`.
- `POST /api/cases/{case_id}/confirm` validates the complete stored baseline.
  Missing fields return `validation_error` with `missing_fields`; a valid
  intake becomes `confirmed`, while a confirmed case remains idempotent.
- `POST /api/cases/{case_id}/documents` requires exactly one multipart `file`
  field. It accepts only PDF, TXT, DOCX, JPG/JPEG, and PNG when the file
  extension matches the declared MIME type. A successful upload turns a draft
  into intake without changing its baseline version.
- A document response and list entry contain only `id`, `case_id`,
  `original_filename`, `content_type`, `size_bytes`, `storage_status`, and
  `created_at`. They never reveal the storage path, internal object name, or
  attachment contents.
- Documents are raw case-private objects only. They must not enter global
  catalog data, scenario snapshots, simulation payloads, or world-role
  contexts.

### 4. Validation & Error Matrix

| Condition | HTTP | Error code |
| --- | ---: | --- |
| Case name, JSON body, baseline key, document type, MIME, filename, or size is invalid | 400 | `validation_error` |
| Request exceeds `MAX_CONTENT_LENGTH` | 413 | `payload_too_large` |
| Case does not exist | 404 | `not_found` |
| Confirmed case baseline is updated or a document is uploaded after confirmation | 409 | `invalid_state` |
| Knowledge-base storage is disabled, invalid, or unavailable | 503 | `storage_unavailable` |
| Local object or metadata write fails | 500 | `storage_error` |

### 5. Good / Base / Bad Cases

- Good: create a draft, upload `resume.pdf`, patch its manual baseline over
  multiple requests, confirm it, and then use the unchanged path/scenario APIs.
- Base: create a case with a complete baseline using the original request
  shape, confirm it, and verify its existing simulation flow still works.
- Bad: upload a Windows-style path filename, an empty attachment, two `file`
  fields, or an extension/MIME mismatch; each request fails without retained
  document metadata or final object files.

### 6. Tests Required

- Assert draft creation, partial baseline merging, confirmation-time missing
  fields, version increments, idempotent confirmation, and rejected confirmed
  baseline edits.
- Assert the five allowed document classes upload with safe metadata and raw
  bytes in their own case collection.
- Assert duplicate display names do not overwrite objects and two cases cannot
  share collection objects.
- Assert malformed multipart payloads, unsafe names, empty and oversized files,
  multiple files, nonexistent cases, disabled storage, and 413 requests return
  their documented error envelopes.
- Run the existing career API integration suite to confirm no external provider
  dependency or scenario behavior changed.

### 7. Wrong vs Correct

#### Wrong

```python
object_path = collection_directory / uploaded_file.filename
object_path.write_bytes(uploaded_file.read())
```

This trusts a client-controlled filename, loads the whole attachment in memory,
and can expose path traversal or partial-file failures.

#### Correct

```python
document_id = generate_document_id()
temporary_file = create_file_in_case_collection()
copy_upload_in_bounded_chunks(temporary_file)
atomically_replace_final_object(document_id)
write_safe_metadata(document_id)
```

The storage service controls paths, enforces the byte limit while streaming,
and exposes only safe metadata through the API.
