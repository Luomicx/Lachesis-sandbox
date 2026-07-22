# Implement Lachesis Backend MVP

## Goal

Build the first executable backend vertical slice for Lachesis: ingest a
career case, create two candidate paths, run a small deterministic world batch,
and retrieve a comparison with provenance and version metadata.

## What I Already Know

- Lachesis is a career-simulation product, not a recommendation engine.
- The project specifications require case isolation, immutable scenario
  versions, rule-owned metrics, and reproducible seeded runs.
- The existing repository includes a Flask backend inherited from MiroFish;
  it currently contains reference models, text parsing, and a Zep adapter but
  no Flask application factory, route layer, dependency manifest, or tests.
- The copied `project.py` and `task.py` models import configuration and locale
  modules that are not present in this standalone workspace. They are source
  references, not directly runnable runtime dependencies.
- `MiroFish-example/` is the concrete implementation reference. It contains a
  Flask application factory, configuration, Blueprint routing, a manager and
  runner lifecycle, and local simulation artifacts that Lachesis should adapt.
- The first documented vertical slice compares a graduate-school path and a
  hypothetical Offer path with ten one-year worlds.

## Assumptions (Temporary)

- The first backend increment will use local persisted JSON/JSONL data and a
  deterministic rule engine. It will not require an external knowledge base,
  LLM, or Mesa/SimPy dependency until the integration boundary is ready.
- Existing MiroFish APIs remain available while the new career API is added in
  parallel.
- Reuse MiroFish's application and lifecycle patterns, but replace Zep Cloud,
  OASIS, Twitter, and Reddit contracts with Lachesis' local knowledge-base and
  career-world boundaries.

## Open Questions

- Confirm the desired first delivery boundary after repository inspection.

## Requirements (Evolving)

- Add a bounded, testable career backend vertical slice.
- Build a Flask API, local JSON/JSONL persistence, validated career domain
  models, and a deterministic seeded runner for the first slice.
- Preserve existing backend behavior and avoid direct dependencies on Zep
  Cloud, OASIS, Twitter, or Reddit types in new career modules.
- Persist case, scenario, run, event, and aggregate versions locally.
- Represent simulated outcomes as distributions and source-labelled values,
  never recommendations or deterministic promises.

## Acceptance Criteria (Evolving)

- [ ] A case can be created from validated baseline input.
- [ ] A graduate-school path and a hypothetical Offer path can be created.
- [ ] A seeded batch produces reproducible one-year results and event logs.
- [ ] A comparison endpoint reports aggregate metrics, failed seeds, and
  version metadata.
- [ ] Automated tests cover the primary path and validation failures.

## Definition of Done

- Tests added or updated for changed behavior.
- Lint, type checks, and relevant backend tests pass.
- API and persistence contracts are recorded in Trellis specifications.
- Existing MiroFish endpoints are not regressed.

## Out of Scope (Temporary)

- Local knowledge-base integration and document ingestion.
- LLM-based intake, role generation, and dialogue.
- Full Mesa/SimPy multi-agent runtime.
- Frontend implementation and report/PDF export.

## Technical Approach

- Adapt MiroFish's Flask factory and manager/runner separation, but create a
  standalone Lachesis package rather than importing its application modules.
- Use local artifact directories per case and scenario. Persist immutable
  inputs, world events, and aggregate results in JSON/JSONL.
- Implement deterministic domain rules first. The future Mesa/SimPy adapter
  will replace the runner behind the same service boundary.

## Decision (ADR-lite)

**Context**: The original reference application depends on Zep Cloud and
OASIS, while the standalone Lachesis workspace has no runnable API scaffold.

**Decision**: Deliver a local, deterministic backend vertical slice before
introducing external knowledge-base services, LLMs, or a full agent runtime.

**Consequences**: The initial API can be tested without infrastructure and
will preserve the correct product contracts. It intentionally does not claim
that local RAG or Mesa/SimPy integration is complete.

## Technical Notes

- Project specifications: `.trellis/spec/lachesis/index.md`.
- Source product requirement: `.trellis/tasks/07-21-lachesis-foundation/prd.md`.
- Source implementation plan: `.trellis/tasks/07-21-lachesis-foundation/research/source-documents/mirofish-retrofit-plan.md`.
- Reference implementation: `MiroFish-example/backend/app/__init__.py`,
  `MiroFish-example/backend/app/config.py`,
  `MiroFish-example/backend/app/api/`, and
  `MiroFish-example/backend/app/services/simulation_manager.py`.
- Reusable patterns: Flask app factory, CORS and health endpoint, Blueprint
  registration, explicit configuration validation, manager/runner lifecycle,
  and local artifact directories.
- Do not migrate: `zep-cloud`, `camel-oasis`, ZEP API-key validation, or any
  Twitter/Reddit request, response, or persistence contract.
- Inspected: `backend/app/models/project.py`, `backend/app/models/task.py`,
  `backend/app/services/text_processor.py`, and
  `backend/app/utils/file_parser.py`.
- The standalone project must establish its own Flask configuration, package
  layout, and test harness before the preserved modules can be integrated.
