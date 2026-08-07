# Implement Case Document Intake and Draft Profiles

## Goal

Add a local, case-isolated document intake flow and manually completable
career baseline. Users can store approved raw attachment formats and update a
draft baseline in multiple requests, but only a complete, validated baseline
can be confirmed and used for existing paths, scenarios, and simulations.

## What I Already Know

- The Flask backend persists cases and simulations as local JSON/JSONL
  artifacts and has no external runtime dependencies beyond Flask.
- The completed local knowledge-base task provides a filesystem-backed,
  case-isolated collection under the configured data directory. It rejects
  unsafe case IDs and reports ready, unavailable, and invalid health states.
- Existing case creation requires a complete baseline and creates an `intake`
  case. Confirmation is currently a state transition only.
- Existing path and scenario creation already require `confirmed` cases and
  must remain unchanged.
- The user selected storage-only documents with PDF, TXT, DOCX, JPG, and PNG
  support. Automatic parsing, OCR, indexing, retrieval, LLM use, and external
  services remain excluded.

## Requirements

- `POST /api/cases` must allow a name-only `draft` case while keeping the
  existing complete `{name, baseline}` request compatible as an `intake` case.
- `PATCH /api/cases/{case_id}` must accept partial baseline updates only for
  `draft` and `intake` cases, merge them into the stored baseline, and advance
  `baseline_version` after an actual change.
- `POST /api/cases/{case_id}/confirm` must validate the complete baseline and
  return a safe `missing_fields` list for incomplete input. Confirmed baselines
  must not be overwritten by the draft-update endpoint.
- Add multipart `POST /api/cases/{case_id}/documents` for exactly one `file`
  field and metadata-only `GET /api/cases/{case_id}/documents`.
- Documents may be uploaded only to `draft` and `intake` cases. Store every
  object and its metadata in the corresponding knowledge-base collection;
  never use a client filename as a filesystem path.
- Allow PDF, TXT, DOCX, JPG/JPEG, and PNG only. Enforce extension and declared
  MIME consistency, reject empty files, restrict one file to 10 MiB, and keep
  the global request size limit at 50 MiB.
- Return safe document metadata only: generated document ID, case ID, cleaned
  display filename, server-classified MIME type, byte size, timestamp, and
  `storage_status: stored`. Never return absolute paths, storage names, or raw
  attachment content.
- If knowledge-base storage is disabled or non-ready, return a clear 503 error
  and never fall back to another directory. Map an over-limit request to the
  standard error envelope with status 413.
- Raw attachments must not be parsed, logged, indexed, placed in global data,
  added to scenario snapshots, fed into simulations, or exposed to world roles.

## Acceptance Criteria

- [x] Name-only cases create a `draft`; legacy complete-baseline case creation
  remains compatible and yields an `intake` case.
- [x] Partial baseline updates work only before confirmation and increment the
  baseline version only when data changes.
- [x] Confirmation reports missing fields safely and changes a complete intake
  case to `confirmed` idempotently.
- [x] Each allowed document type uploads into its own case collection and the
  list endpoint returns safe metadata without physical storage details.
- [x] Invalid multipart bodies, unsafe names, type mismatches, empty files,
  file-size violations, and multiple files return validation errors without
  retained objects or metadata.
- [x] Unknown cases return 404; disabled or invalid knowledge-base storage
  returns 503 without writing documents.
- [x] Existing case -> confirm -> path -> scenario -> run tests still pass
  without network, LLM, OCR, Neo4j, Qdrant, or legacy provider imports.
- [x] Tests cover a 413 request-limit response, cross-case isolation, duplicate
  display names, and rejection of baseline edits after confirmation.

## Definition of Done

- Tests, compilation checks, specification updates, and an implementation
  review pass.
- The full existing career API suite remains green.
- No upload response, exception, or artifact exposes a local absolute path or
  raw attachment content.

## Out of Scope

- PDF, DOCX, image, or text parsing; OCR; extraction; automatic profile
  prefill; modelling-agent dialogue; and LLM calls.
- Local RAG, vector embeddings, text search, graph writes, Neo4j, Qdrant, or
  any external provider.
- Document download, export, deletion, account ownership, multi-device sync,
  or global catalog ingestion.
- Changing deterministic scenario input, simulation, report, or world-role
  behavior.

## Technical Notes

- Use the case collection supplied by
  `backend/app/services/knowledge_base.py`, not the legacy `zep_adapter`.
- Follow the current app-extension pattern in `backend/app/__init__.py` and
  the `unittest` temporary data-directory pattern in `backend/tests/`.
- The existing 50 MiB `MAX_CONTENT_LENGTH` is request-scoped. The new 10 MiB
  document limit must be enforced while copying the file stream, not by loading
  the full object in memory.
- Update the executable product, API, knowledge-base, and delivery specs as
  part of this task.
