# Directory Structure

> How backend code is organized in this project.

---

## Overview

<!--
Document your project's backend directory structure here.

Questions to answer:
- How are modules/packages organized?
- Where does business logic live?
- Where are API endpoints defined?
- How are utilities and helpers organized?
-->

(To be filled by the team)

---

## Directory Layout

```
<!-- Replace with your actual structure -->
src/
├── ...
└── ...
```

---

## Module Organization

<!-- How should new features/modules be organized? -->

(To be filled by the team)

---

## Naming Conventions

<!-- File and folder naming rules -->

(To be filled by the team)

---

## Examples

<!-- Link to well-organized modules as examples -->

(To be filled by the team)

---

## Established Lachesis Backend Convention

```text
backend/
├── app/
│   ├── api/        # Flask Blueprints and HTTP validation only
│   ├── models/     # Domain validation and shared domain constants
│   ├── services/   # Persistence and simulation orchestration
│   ├── config.py   # Environment-backed application settings
│   └── __init__.py # Flask application factory and error registration
├── tests/          # Black-box Flask API integration tests
├── run.py          # Local development entry point
└── requirements.txt
```

- API modules validate request shape and translate service results to JSON.
- Services own artifact paths and rule execution; API modules must not access artifact paths directly.
- Models hold validation rules and shared domain constants. New career modules must not import the legacy MiroFish project/task models.
- Runtime artifacts belong under `backend/data/`, configured by `LACHESIS_DATA_DIR`, and are never committed.
