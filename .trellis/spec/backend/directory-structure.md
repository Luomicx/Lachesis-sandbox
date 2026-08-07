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

## 文件头注释约定（必需）

> 每个 `.py` 文件的开头都必须使用中文注释说明**该文件所在目录（文件夹）的用途**，
> 以及本文件在其中扮演的角色。整个项目内的代码注释统一使用**中文**。

- 文件头注释放置在文件最顶部，`from __future__ import annotations` 等导入之前。
- 内容至少包含：所在文件夹的用途 + 本文件的具体职责。
- 全项目代码注释（含行内注释、函数 docstring）一律使用中文，禁止使用英文注释。

示例：

```python
"""
models/ 目录：领域模型层。
本文件定义 case 领域的验证规则与共享常量，
供 API 与 service 层复用，禁止被 legacy 模型依赖。
"""
from __future__ import annotations
```

```python
# services/ 目录：持久化与仿真编排层。
# 本文件负责文档摄入，落盘到对应 case 的知识库集合。
from __future__ import annotations
```

> 新增 `backend/app/` 下的 `.py` 文件必须附带该文件头注释；
> 已有的旧文件在后续修改时逐步补齐，并同步将英文注释改为中文。

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
