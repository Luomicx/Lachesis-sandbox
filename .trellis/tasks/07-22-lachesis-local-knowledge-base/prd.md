# Plan Lachesis Local Knowledge Base

## Goal

Define and implement the next backend slice: a local knowledge-base boundary
for career cases, with explicit health checks and no direct dependency from
career services on legacy providers.

## What I Already Know

- The completed backend MVP persists case and simulation artifacts locally and
  intentionally has no knowledge-base, LLM, Neo4j, or Qdrant dependency.
- The project includes a copied `backend/app/services/zep_adapter/` reference
  implementation. Lachesis specifications require business services to use a
  local knowledge-base facade rather than provider-specific imports.
- The source roadmap calls for a health check before document ingestion and
  intake workflows are added.
- The user requested continuation of backend development through a new
  Trellis task on 2026-07-22.
- Importing the copied `zep_adapter` currently crosses into Neo4j, Qdrant, and
  legacy logging dependencies, so new career services must not import it.

## Scope Decision

This increment establishes the provider-neutral boundary and its offline
behavior first. The default implementation must use only the local filesystem
and standard-library facilities; it must not import or start Neo4j, Qdrant,
embedding, LLM, or legacy Zep adapter dependencies.

External providers can be added in a later increment behind the same boundary.
They are explicitly not a runtime prerequisite for the existing Flask MVP.

## Requirements

- Add a case-isolated knowledge-base facade with a documented health contract.
- Register the configured facade through the Flask application extensions.
- Provide a default filesystem-backed implementation that creates a dedicated
  namespace below the configured local data directory.
- Extend the existing health endpoint with structured knowledge-base health
  information while preserving its current top-level response fields.
- Treat unknown or internally unavailable providers as explicit `invalid` or
  `unavailable` health states; application startup must remain safe for the
  existing local MVP.
- Keep provider details out of career API, repository, and simulation services.

## Acceptance Criteria

- [x] A documented knowledge-base interface exists.
- [x] The backend can report local dependency health without external services.
- [x] Existing career API tests continue to pass without external services.
- [x] Tests cover ready, unavailable, and invalid health states without
  requiring network access or external services.

## Definition of Done

- Tests, compile checks, and specification updates pass.
- No new direct imports of Zep Cloud, OASIS, Twitter, or Reddit types appear
  in career services.

## Out of Scope

- User document upload and intake dialogue.
- Production Neo4j/Qdrant deployment and catalog administration.
- LLM-based extraction, entity generation, or world-role retrieval.

## Technical Notes

- Project contract: `.trellis/spec/lachesis/local-knowledge-base.md`.
- Reference implementation: `backend/app/services/zep_adapter/`.
- Existing `career` API handlers resolve only the repository and deterministic
  simulation service from the Flask application extensions.
- Previous backend task: `.trellis/tasks/archive/2026-07/07-21-implement-lachesis-backend/`.
- The existing `zep_adapter` imports undeclared Neo4j, Qdrant, OpenAI, and
  embedding dependencies and references an absent logger utility. It is a
  reference only and must remain outside the new application startup path.
- Reuse the application-factory and `app.extensions` conventions in
  `backend/app/__init__.py`, plus the `unittest` temporary-data-dir pattern in
  `backend/tests/test_career_api.py`.
