# Lachesis Project Specifications

> Authoritative project constraints for the Lachesis career-simulation product.

## Use This Specification

Read the documents that apply to the change before implementation. The product
and delivery documents apply to every user-facing change. Backend work should
also read the domain, knowledge-base, and CareerWorld documents; frontend work
should also read the product and domain documents.

| Document | Scope |
| --- | --- |
| [Product](./product.md) | User scope, non-goals, simulation disclosures, and interaction rules. |
| [Architecture](./architecture.md) | Module boundaries and prohibited legacy dependencies. |
| [Domain and API](./domain-and-api.md) | Core entities, lifecycle states, API surface, and versioning. |
| [Local Knowledge Base](./local-knowledge-base.md) | Case isolation, evidence provenance, and adapter contract. |
| [CareerWorld](./careerworld.md) | Simulation engine, reproducibility, event rules, and branching. |
| [Delivery](./delivery.md) | Delivery order and acceptance criteria. |
| [Tooling and Workflow](./tooling-and-workflow.md) | Git repository and Trellis developer setup required for task lifecycle operations. |

## Non-Negotiable Constraints

- Do not present rankings, recommendations, or deterministic admissions or
  career outcomes.
- Keep user data isolated per case; only reviewed official data can become a
  global catalog input.
- The rule engine is the sole writer of conclusion-level metrics. LLM output
  is a validated proposal or narrative only.
- Preserve immutable scenario and report versions. A branch must never mutate
  a baseline world.
- Do not couple new career modules to Zep Cloud, OASIS, Twitter, or Reddit
  platform types.
