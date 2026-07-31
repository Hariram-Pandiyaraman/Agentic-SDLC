# Codex Prompt and Refinement Log

## Purpose

This document records significant prompts sent to Codex, the substance of Codex's responses, and user refinements that materially affect the solution. It is intended to preserve design intent and decision history, not internal model reasoning or low-level tool output.

Sensitive values, credentials, and private data must be redacted before adding them to this log.

## Interaction Log

### Entry 001 — Initial Documentation Request

**Date:** 2026-07-29

**User prompt**

> Here the Specification. Based on given, Create the following Architecture.md, Plan.md, Readme.md, Prompts.md (Log of all significant prompts sent to Codex, responses, and refinements.), .gitignore. Ask me for the Tech stack

The attached specification described an 11-agent SDLC automation framework covering requirement intake, contextual knowledge retrieval, clarification, BRD creation, story and sprint planning, code generation, Git operations, review, sanity testing, defect creation, release handoff, and knowledge graph lineage. It constrained the first delivery to a one-day PoC with approximately two to three hours of implementation effort, local Ollama inference, deterministic fallbacks, mock data, and architect approval gates.

**Codex response**

Codex reviewed the specification and confirmed that the workspace was empty except for Git metadata. It requested the following stack decisions:

- Frontend
- Backend/API
- Agent orchestration framework
- Local Ollama model
- Knowledge graph/database
- Testing framework
- Deployment/container approach

Codex also offered to choose a practical hackathon stack if the user preferred a recommendation.

**Outcome**

Documentation creation was intentionally deferred until the user supplied the desired stack.

### Entry 002 — Technology Stack Refinement

**Date:** 2026-07-29

**User prompt**

> Frontend - Streamlit  
> Backend/API - FastApi(Python)  
> Agent Framework - LangGraph  
> local Ollama model  
> Knowledge graph/database - neo4j  
> Testing framework - any open source  
> Deployment/container approach - docker(no avl in my local)

**Codex response**

Codex selected:

- Streamlit for the UI.
- FastAPI and Python for the API.
- LangGraph for orchestration and HITL interrupts.
- Ollama for local inference, with `qwen2.5-coder:7b` as a configurable recommended default.
- Neo4j for retrieval and artifact lineage.
- Pydantic for typed contracts.
- pytest as the open-source testing framework.
- Native local processes as the primary development path.
- Docker/Docker Compose as optional deployment packaging because Docker is not available in the user's local environment.

Codex then created the requested architecture, delivery plan, README, prompt log, and Git ignore rules.

**Key refinements captured**

- Docker must not be required to develop or demonstrate the PoC locally.
- All model and graph integrations require deterministic/local fallback paths.
- Git mutations default to dry-run.
- Architect approval gates occur after clarification, BRD generation, and code planning.
- The Release Agent also persists graph lineage, keeping the design at exactly 11 agents.

## Logging Convention for Future Work

Add a new entry when a prompt:

- Changes architecture, scope, stack, workflow, or acceptance criteria.
- Requests implementation of a major component.
- Resolves an important ambiguity or tradeoff.
- Reports a significant failure and results in a design refinement.
- Approves or rejects a major generated artifact.

Each entry should use:

```markdown
### Entry NNN — Short Title

**Date:** YYYY-MM-DD

**User prompt**

> Exact prompt or a faithful concise excerpt

**Codex response**

Concise summary of the delivered response or changes. Do not include hidden reasoning.

**Refinement / outcome**

Decisions made, files changed, validation performed, and any unresolved items.
```

Minor formatting requests, repeated status checks, raw command output, and credentials should not be logged.

### Entry 003 — Execute Phase 0

**Date:** 2026-07-29

**User prompt**

> Execute Phase 0 plan quickly. We have only five mins for this phase

**Codex response**

Codex implemented the Phase 0 repository skeleton:

- FastAPI entry point with root and dependency-health endpoints.
- Streamlit readiness UI.
- Typed Pydantic Settings configuration and `.env.example`.
- Dependency manifest and project package structure.
- Ollama and Neo4j readiness checks with safe degraded behavior.
- Initial pytest smoke tests.
- A project-local virtual environment with Streamlit installed.

**Refinement / outcome**

The machine has Python 3.14, FastAPI, Uvicorn, Pydantic Settings, and HTTPX. Ollama and Neo4j are not installed or reachable, so local fixture context and deterministic template fallback are enabled by default. Three Phase 0 tests passed; later phases can proceed without waiting for those external services.

### Entry 004 — Execute Phase 1

**Date:** 2026-07-29

**User prompt**

> Execute phase 1 as planned

**Codex response**

Codex implemented strict Pydantic domain models, stable artifact IDs, atomic per-run artifact storage, source linkage, fixture context retrieval, JSON lineage persistence, and optional Neo4j context/lineage adapters with constraints and mock seed data.

**Refinement / outcome**

The offline path remains the default because Neo4j is unavailable locally. Artifact revisions reuse a stable ID and increment only that artifact's version. Focused tests validate requirement parsing, IDs, artifact persistence and linkage, revision behavior, fixture retrieval, and local lineage.

### Entry 005 — Execute Phase 2

**Date:** 2026-07-29

**User prompt**

> Execute phase 2 as planned. Use Hugging Face Transformers if required.

**Codex response**

Codex implemented the checkpointed LangGraph workflow with all 11 agent responsibilities, three `interrupt`-based HITL gates, approval and rejection routing, bounded retries, deterministic fallback outputs, run start/resume inspection, and final QA/lineage generation.

**Refinement / outcome**

Hugging Face Transformers was not required for Phase 2 because orchestration and deterministic offline generation are fully implemented without a model runtime. LangGraph's installed native `interrupt`, `Command`, and `InMemorySaver` APIs are used. Workflow tests cover the approved path, scope revision, simulated test failure, retry fallback, and decision validation.

### Entry 006 — Execute Phase 3

**Date:** 2026-07-29

**User prompt**

> Proceed phase 3

**Codex response**

Codex implemented versioned prompts for intake, context ranking, clarification, BRD, stories, planning, code planning, implementation, review, sanity, and release. A structured Ollama gateway now enforces JSON Schema output, performs one repair attempt, and activates typed deterministic fallbacks when generation is disabled or unavailable.

**Refinement / outcome**

Ollama remains disabled by default because it is not installed locally. Every generative artifact records provider, model, prompt version, attempts, repair usage, latency, errors, and fallback status. Acceptance-criterion validation confirms IDs appear across implementation metadata and comments, test mappings, review findings, and QA handoff. Hugging Face Transformers was not needed.

### Entry 007 — Execute Phase 4

**Date:** 2026-07-29

**User prompt**

> Proceed phase 4.

**Codex response**

Codex implemented the operational FastAPI and Streamlit layer. The API supports run creation, status inspection, approval resume, exact artifact-version retrieval, lineage, and ZIP export. Streamlit supports requirement text/file submission, workflow progress, approvals and rejections, grouped artifact review, downloads, and lineage visualization.

**Refinement / outcome**

An application factory isolates API tests while the production app retains one process-local workflow runner for HITL checkpoints. Rejected BRDs are available as distinct retrievable versions. Windows atomic persistence was hardened for both manifests and lineage files. The Streamlit initial render completes without exceptions.

### Entry 008 — Correct Global Python Launch

**Date:** 2026-07-29

**User prompt**

The user reported that `uvicorn api.main:app --reload --port 8000` launched from
global Python and failed with `ModuleNotFoundError: No module named 'langgraph'`.

**Codex response**

Codex identified the interpreter mismatch and added PowerShell launch scripts
that invoke the API and UI directly from the project virtual environment.

**Refinement / outcome**

The documented startup path no longer depends on PowerShell activation or
`PATH` ordering. `scripts/run_api.ps1` and `scripts/run_ui.ps1` always use the
project-local executables.

### Entry 009 — Execute Phase 5

**Date:** 2026-07-29

**User prompt**

> Proceed phase 5 now.

**Codex response**

Codex added the seeded requirement, five-minute demo narrative, one-command
offline demo runner, handoff-readiness validator, complete prompt-contract
test, passing and failed-sanity demo tests, and deterministic UI source checks.
It also performed real HTTP startup probes against FastAPI and Streamlit using
the project virtual environment.

**Refinement / outcome**

Both native servers responded successfully. The failed-sanity demo completed,
created `DEF-001`, generated `QA-001`, and passed final handoff validation.
Direct Python utility scripts were hardened to resolve the project package
without relying on `PYTHONPATH`. Because Ollama is not installed, its structured
path is contract-tested with mock responses rather than a live model.
