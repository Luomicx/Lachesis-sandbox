# Tooling and Workflow Contract

## Scenario: Initialize a Lachesis Development Workspace

### 1. Scope / Trigger

- Trigger: a project workspace is missing Git metadata or the Trellis
  developer identity.
- Why this needs a code-spec: Trellis task creation, session context, journals,
  and completion commits rely on these two local integrations. Missing setup
  leaves the workflow partially functional and hides the failure until a task
  or commit operation runs.

### 2. Signatures

Run these commands from the repository root:

```powershell
git init
python ./.trellis/scripts/init_developer.py <developer-name>
python ./.trellis/scripts/get_context.py
```

The developer initialization command creates `.trellis/.developer` and
`.trellis/workspace/<developer-name>/`. The identity file is intentionally
ignored by `.trellis/.gitignore` and must not be staged.

### 3. Contracts

| Item | Required contract |
| --- | --- |
| Repository root | `.git/` exists and `git rev-parse --is-inside-work-tree` returns `true`. |
| Developer identity | `.trellis/.developer` names the local developer; use `slias` for this workspace unless intentionally changing the identity. |
| Task creation | Run `task.py create` only after developer initialization, or pass an explicit `--assignee`. |
| Commit scope | Commit project content and task artifacts deliberately. Do not commit `.trellis/.developer`, `.trellis/.runtime/`, or other ignored runtime state. |

### 4. Validation & Error Matrix

| Condition | Expected behavior | Correct action |
| --- | --- | --- |
| `git rev-parse --is-inside-work-tree` fails | Git status and Trellis commit steps cannot resolve repository state. | Run `git init` at the Lachesis root. |
| `.trellis/.developer` is absent | `get_context.py` reports `Developer: Not initialized`; task creation without `--assignee` fails. | Run `init_developer.py <developer-name>`. |
| Developer identity already exists | Initialization exits without replacing the identity. | Keep the existing identity or intentionally remove and reinitialize it outside normal task work. |
| Git repository has no commits | `git status` shows untracked project files. | Review `.gitignore`, stage intentionally, then create an explicit initial commit. |

### 5. Good / Base / Bad Cases

- Good: `.git/` exists, `slias` is initialized, `get_context.py` shows the
  developer and current task, and `git status --short` runs from the root.
- Base: Git is initialized but has no commits; Trellis planning can proceed,
  while initial staging and commit remain an explicit user decision.
- Bad: starting a task in a non-Git root with no developer identity. Context
  reports initialization failure and the finish/commit lifecycle is unusable.

### 6. Tests Required

- Run `git rev-parse --is-inside-work-tree` and assert `true`.
- Run `python ./.trellis/scripts/get_context.py` and assert that the
  developer name is present with no initialization error.
- Run `python ./.trellis/scripts/task.py list --mine` and assert it resolves
  tasks for the configured developer.
- Before an initial commit, run `git status --short` and review every path;
  assert that no ignored Trellis runtime file is staged.

### 7. Wrong vs Correct

#### Wrong

```powershell
python ./.trellis/scripts/task.py create "Implement career intake"
# Error: No developer set
```

#### Correct

```powershell
git init
python ./.trellis/scripts/init_developer.py slias
python ./.trellis/scripts/task.py create "Implement career intake"
```

The correct sequence makes the task attributable to a local developer and
keeps the repository ready for Trellis' later commit and archive steps.
