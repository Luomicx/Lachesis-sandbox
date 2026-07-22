# Lachesis

[![Repository](https://img.shields.io/badge/GitHub-Luomicx%2FLachesis--sandbox-181717?logo=github&logoColor=white)](https://github.com/Luomicx/Lachesis-sandbox)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?logo=flask&logoColor=white)
![Status](https://img.shields.io/badge/Status-Backend%20MVP-2ea44f)

Repository: [github.com/Luomicx/Lachesis-sandbox](https://github.com/Luomicx/Lachesis-sandbox)

Lachesis is a personal career-simulation sandbox for undergraduate students in
computer science, software engineering, and AI-related fields in mainland
China. It models alternative education and employment paths as reproducible,
branchable worlds. It shows assumptions, distributions, and turning points; it
does not rank paths, make decisions, or promise admissions or career outcomes.

## Why Lachesis

**Lachesis** is one of the Moirai, the three Greek goddesses of fate. She is
responsible for measuring the thread of life: its length and its decisive
moments. That metaphor fits this project directly. Lachesis measures how the
length and quality of a life trajectory can change under different choices,
constraints, and uncertainty.

Unlike familiar names such as Apollo or Athena, Lachesis is a quieter
mythological reference. It signals that this product is about examining the
conditions around a life path, not claiming to control anyone's destiny.

## Product Principles

- Compare up to four study, Offer, and fallback paths over 1, 3, or 5 years.
- Express outcomes as simulated distributions, not single-point promises.
- Keep user facts, official data, model assumptions, and simulation results
  distinguishable and traceable.
- Allow only controllable causes to change in a branch. Admissions, income,
  and promotions are computed outcomes, never manually overwritten.
- Keep sensitive case data isolated. World roles receive derived context only.
- Never expose a total score, path ranking, or recommendation button.

## Current Status

The first local backend vertical slice is available. It provides:

- A standalone Flask application and health endpoint.
- Career Case creation and confirmation with validated baseline data.
- Graduate-school and real or hypothetical Offer paths, each carrying an
  explicit provenance label.
- Immutable scenario snapshots and local JSON/JSONL artifacts.
- Deterministic 10/20/50-seed batches over 1/3/5-year horizons.
- Aggregate distributions and individual world timelines.

The local knowledge base, document intake, LLM-based modelling, Neo4j/Qdrant,
Mesa/SimPy runtime, report export, and frontend integration are planned next.

## Architecture

```text
Vue UI (planned)
  -> Flask API
       -> Career Case / Path / Scenario services
       -> Local JSON and JSONL artifacts
       -> Deterministic CareerWorld runner
       -> Future adapters: local knowledge base and Mesa + SimPy
```

The implementation takes structural inspiration from `MiroFish-example/`:
Flask app factory, API/service separation, local artifact lifecycle, and
simulation orchestration. Its Zep Cloud, OASIS, Twitter, and Reddit domain
contracts are deliberately not dependencies of Lachesis.

## Run The Backend

Requirements: Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python backend/run.py
```

The development server listens on `http://127.0.0.1:5001` by default.

```powershell
Invoke-RestMethod http://127.0.0.1:5001/health
python -m unittest discover -s backend/tests -v
```

Runtime data defaults to `backend/data/` and is ignored by Git. Set
`LACHESIS_DATA_DIR` to use a different local artifact directory.

## Initial API Surface

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/cases` | Create a case with its baseline. |
| `POST` | `/api/cases/{case_id}/confirm` | Confirm the baseline before modelling paths. |
| `POST` | `/api/cases/{case_id}/paths` | Add a graduate-school or Offer path. |
| `POST` | `/api/scenarios` | Create an immutable scenario snapshot. |
| `POST` | `/api/scenarios/{scenario_id}/runs` | Run a quick, standard, or deep batch. |
| `GET` | `/api/scenarios/{scenario_id}/comparison?batch_id=...` | Retrieve distributions and run metadata. |
| `GET` | `/api/world-runs/{world_id}/timeline` | Retrieve events and snapshots for one world. |

The executable request, validation, and error contracts live in
[`.trellis/spec/lachesis/domain-and-api.md`](.trellis/spec/lachesis/domain-and-api.md).

## Repository Layout

```text
backend/             Flask API, domain rules, persistence, runner, and tests
frontend/            Frontend reference assets; integration is pending
spec/                Product and architecture source specifications
.trellis/spec/       Executable project and backend development contracts
MiroFish-example/    Local reference implementation; excluded from this repository
```

## Development Workflow

The project uses Trellis for task, specification, and session management. Read
[`AGENTS.md`](AGENTS.md) before development. Project-specific contracts are
indexed at [`.trellis/spec/lachesis/`](.trellis/spec/lachesis/).
