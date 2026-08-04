# SDLC Agentic Framework

An end-to-end agentic SDLC proof of concept that converts a raw feature requirement into structured, traceable delivery artifacts. Eleven LangGraph agents coordinate intake, context retrieval, clarification, BRD creation, backlog planning, code generation, review, sanity validation, release handoff, and Neo4j knowledge capture.

Application version: **0.2.1** (delivery Phases 0 through 3 complete; later phases remain in development).

This repository contains the architecture, implementation plan, and Phase 0 application skeleton for the PoC.

## What the PoC Demonstrates

- Requirement normalization from text or a text-based upload.
- Retrieval of related mock knowledge from Neo4j.
- Architect-controlled scope, BRD, and code-plan approval gates.
- Versioned BRD, epics, stories, subtasks, and Given-When-Then acceptance criteria.
- Sprint and implementation planning.
- Generated implementation stub and unit-test mapping.
- Traceable code review, sanity results, and structured defects.
- Release notes and a QA handoff.
- Complete lineage from requirement to release.
- Local Ollama inference with deterministic template fallbacks.

## Technology Stack

- **UI:** React 19 and Vite with a responsive liquid-glass design system
- **API:** FastAPI with Python
- **Orchestration:** LangGraph
- **Persistence:** SQLAlchemy 2.x, Alembic, and SQLite by default
- **Local model:** Ollama; `qwen2.5-coder:7b` is the recommended configurable default
- **Knowledge graph:** Neo4j
- **Validation:** Pydantic
- **Testing:** pytest
- **Packaging:** Docker and Docker Compose as optional deployment artifacts

Docker is not required for local development. The primary setup uses native Python processes plus locally installed Ollama and Neo4j.

## Agent Workflow

1. Intake Agent normalizes the requirement.
2. Context Agent retrieves related knowledge.
3. Clarification Agent resolves scope and assumptions.
4. BRD Agent creates the versioned BRD.
5. Story Agent creates epics, stories, criteria, estimates, and dependencies.
6. Plan Agent creates the sprint plan.
7. Code Agent creates an approved code plan, implementation stub, and tests.
8. Git Agent prepares safe, dry-run Git actions by default.
9. Review Agent checks code against the BRD and acceptance criteria.
10. Sanity Agent maps test results and creates defects.
11. Release Agent creates the release handoff and persists lineage.

The workflow pauses for architect approval after clarification, BRD generation, and code planning.

## Expected Artifacts

Each run produces an indexed set of artifacts:

- Normalized requirement with assumptions, constraints, dependencies, and open questions.
- Related-context pack.
- Versioned BRD with confidence scores and approvals.
- Epics, stories, subtasks, acceptance criteria, estimates, and dependency map.
- Sprint plan and code plan.
- Implementation stub and unit tests.
- Review findings, sanity results, and defects.
- Release notes, QA handoff, and lineage graph.

## Planned Local Setup

These commands describe the intended implementation setup once the application source is added.

### Prerequisites

- Python 3.11+
- Ollama (optional; deterministic generation works without it)
- A locally reachable Neo4j instance
- Git

Docker is optional and may be used later on a machine where it is available.

### 1. Create a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Prepare Ollama

This step is optional. Skip it and retain `USE_OLLAMA=false` to use deterministic templates.

```powershell
ollama pull qwen2.5-coder:7b
ollama serve
```

If another model is already installed, set `OLLAMA_MODEL` to that model instead.

### 3. Configure the application

Copy `.env.example` to `.env` and configure:

```dotenv
APP_ENV=development
API_BASE_URL=http://localhost:8000

OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder:7b
OLLAMA_TEMPERATURE=0.1
USE_OLLAMA=false

NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=change-me

ALLOW_GIT_MUTATIONS=false
USE_FIXTURE_CONTEXT=false
ENABLE_TEMPLATE_FALLBACKS=true
ARTIFACT_ROOT=artifacts
```

Never commit `.env`.

### 4. Seed demo knowledge

```powershell
python scripts/seed_neo4j.py
```

If Neo4j is not available, set `USE_FIXTURE_CONTEXT=true`. The application should then load mock context and save lineage locally.

### 5. Start the API

```powershell
.\scripts\run_api.ps1
```

### 6. Install and start the React UI in another terminal

```powershell
npm install --prefix frontend
.\scripts\run_ui.ps1
```

The API script invokes the executable inside `.venv`; the UI script starts the
workspace-local Vite installation. During development, Vite proxies `/api` and
`/health` requests to FastAPI on port 8000.

Open `http://localhost:5173`.

### 7. Run tests

```powershell
pytest
```

## Configuration and Fallback Behavior

Ollama and Neo4j are accessed through service interfaces. When configured fallbacks are enabled:

- An Ollama timeout, connection error, or invalid structured response activates a deterministic artifact template.
- A Neo4j connection failure activates seeded fixture context and writes lineage to JSON.
- The artifact manifest records all fallback events so demo output is never presented as model-generated when it was produced from a template.

## Repository Documents

- [Architecture.md](Architecture.md) — system structure, agents, workflow, data, lineage, and design constraints.
- [Plan.md](Plan.md) — phased implementation plan, priorities, tests, risks, and demo script.
- [Prompts.md](Prompts.md) — significant Codex interaction log and the maintenance convention.

## Current Status

0.2.1 Phase 0 is complete:

- One explicit `0.2.1` package and API version.
- Workspace-local pytest temp and cache paths for reliable Windows runs.
- Regression contracts for API response shapes, exact artifact versions, content headers, and checksums.
- Designed treatments for first-use, running, approval, rejected, failed, fallback, and complete states.
- Reusable tokens and component contracts with automated WCAG AA contrast checks.
- The compact [UX foundation specification](docs/ux-foundation.md).

0.2.1 Phase 1 is complete:

- Responsive branded application shell with persistent desktop navigation and a tablet menu.
- Dashboard summary cards for active, approval, complete, failure, and fallback signals.
- Recent-run search plus status and date filters, with intentional loading, empty, filtered-empty, and API-unavailable states.
- Guided three-step requirement intake with inline validation, text/Markdown import preview, progressive advanced options, and a clear launch transition.
- Compact service-status popover with full environment diagnostics moved to Settings.

0.2.1 Phase 2 is complete:

- Run header with current stage, elapsed and updated time, fallback count, and a contextual next action.
- Accessible workflow stepper and combined agent/HITL activity timeline.
- Side-by-side approval review with exact artifact/version locking, decision history, and required rejection comments.
- Artifact card/table views, type and producer filters, version history, metadata, formatted/raw presentations, and exact-version downloads.
- Readable Markdown and structured-data renderers for delivery artifacts.
- Grouped, zoomable lineage map with node details and an accessible relationship table fallback.

0.2.1 Phase 3 is complete:

- SQLAlchemy repository interfaces and portable relational tables for runs, artifacts, versions, sources, approvals, fallbacks, checkpoints, and lineage.
- Alembic migrations with zero-setup SQLite startup and an explicit migration command.
- Durable LangGraph snapshots and pending writes that preserve all approval and rejection loops across API restarts.
- Database-backed dashboard, filter, pending-approval, artifact, and lineage queries.
- SQLite foreign keys, WAL mode, bounded busy timeout, short transactions, and rollback coverage.
- Database-authoritative artifact content with filesystem rematerialization for downloads and ZIP exports.

### Relational database setup

SQLite is the zero-configuration default. `DATABASE_URL` may override the connection;
credentials are never returned by health endpoints. Upgrade a fresh or existing database
using the supported Alembic wrapper:

```powershell
.\.venv\Scripts\python.exe -m scripts.migrate_db
```

The API also applies pending migrations during startup. SQLite enables foreign keys, a
five-second busy timeout, WAL journaling, and short repository transactions. Artifact
content and workflow checkpoints are stored in the database; files remain materialized
for exact-version downloads and ZIP export compatibility.

Phase 0 is complete:

- FastAPI application and `/health` readiness endpoint.
- React service-readiness page and environment diagnostics.
- Typed environment configuration.
- Project-local Python virtual environment.
- Dependency manifest and `.env.example`.
- Initial package structure and smoke tests.
- Safe fixture/template fallback defaults.

Phase 1 is complete:

- Strict Pydantic schemas for requirements and downstream traceability artifacts.
- Stable readable artifact IDs and per-artifact revision numbers.
- Atomic per-run artifact storage with an authoritative manifest and checksums.
- Source-artifact validation.
- Ranked fixture-backed context retrieval.
- Local JSON lineage storage.
- Optional Neo4j retrieval, lineage, constraints, and mock seeding.

Phase 2 is complete:

- Typed shared LangGraph workflow state.
- Eleven implemented agent responsibilities.
- Scope, BRD, and code-plan approval interrupts.
- Rejection loops that create revised clarification, BRD, or code-plan artifacts.
- Run checkpointing and programmatic start/resume commands.
- Bounded retry with explicit deterministic fallback.
- Dry-run Git planning and simulated sanity/defect branches.
- Final release notes, QA handoff, and local lineage generation.

Phase 3 is complete:

- Versioned system and task prompts for all generative workflow stages.
- Ollama `/api/chat` integration with JSON Schema output.
- Strict Pydantic validation for generated responses.
- Exactly one repair attempt for malformed structured output.
- Deterministic fallback for disabled or unavailable Ollama.
- Provider, model, prompt version, attempts, repair, latency, errors, and fallback metadata in artifact manifests.
- Acceptance-criterion coverage validation across implementation, tests, review, and QA handoff.
- Traceability guards that preserve IDs in generated code and release handoffs.

Phase 4 is complete:

- FastAPI create, status, resume, artifact, lineage, and export endpoints.
- Process-local workflow runner that preserves HITL checkpoints.
- Guided React text/file requirement submission.
- Agent progress and fallback visibility.
- Scope, BRD, and code-plan approval/rejection panels.
- Exact artifact-revision display and downloads.
- Grouped artifact tabs and Graphviz lineage visualization.
- Complete run export as a ZIP archive.

Phase 5 is complete:

- Seeded feature requirement and five-minute demo narrative.
- One-command deterministic demo runner.
- Passing and failed-sanity demo validation.
- Final handoff-readiness checks for required artifacts, source linkage, AC coverage, and defects.
- Contract coverage for every generative prompt task.
- Clean native FastAPI startup probes and a production React build.
- Full automated regression suite.

Ollama and Neo4j are not currently installed locally, so health reports a degraded service state while the fallback path remains ready. The Ollama structured-generation path is tested with mock model responses; a live Ollama inference test requires installing the Ollama application.

### Run the seeded offline demo

```powershell
.\scripts\run_demo.ps1
```

Exercise the qualified defect branch:

```powershell
.\scripts\run_demo.ps1 --simulate-failure
```

The demo automatically approves all three gates, writes artifacts under
`artifacts/<run_id>/`, and fails its process exit code if the final handoff
validator finds missing artifacts, source links, acceptance-criterion coverage,
or a missing defect.

Demo assets:

- [Sample requirement](examples/sample_requirement.md)
- [Five-minute demo narrative](examples/demo-script.md)

### Workflow API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/v1/runs` | Start a feature workflow |
| `GET` | `/api/v1/runs` | Search and filter durable run summaries |
| `GET` | `/api/v1/approvals/pending` | List runs currently awaiting a decision |
| `GET` | `/api/v1/runs/{run_id}` | Read status, pending approval, state, and artifacts |
| `POST` | `/api/v1/runs/{run_id}/resume` | Approve or reject the current gate |
| `GET` | `/api/v1/runs/{run_id}/artifacts` | List all artifact versions |
| `GET` | `/api/v1/runs/{run_id}/artifacts/{artifact_id}?version=1` | Download an exact artifact version |
| `GET` | `/api/v1/runs/{run_id}/lineage` | Read completed artifact lineage |
| `GET` | `/api/v1/runs/{run_id}/export` | Download the complete run ZIP |

Interactive API documentation is available at `http://localhost:8000/docs`.

The API and React UI must point to the same running FastAPI process because Phase 4 checkpoints use LangGraph's in-memory saver. Generated artifacts remain on disk, but interrupted runs cannot be resumed after an API restart.

### Programmatic workflow example

```python
from sdlc.services.workflow_runner import WorkflowRunner

runner = WorkflowRunner("artifacts")
response = runner.start(
    "Create a traceable feature workflow.",
    title="Traceable workflow",
)

while response["status"] == "waiting_for_approval":
    gate = response["interrupts"][0]["value"]["gate"]
    print(f"Approving {gate}")
    response = runner.resume(
        response["run_id"],
        {
            "status": "approved",
            "actor": "Demo Architect",
            "comment": "Approved for the PoC",
        },
    )

print(response["state"]["artifact_ids"]["qa_handoff"])
```

The current `InMemorySaver` checkpoints survive approval pauses while the Python process remains running. Durable cross-process checkpoints are deferred beyond the PoC.

## Safety Notes

- Model-generated commands must not be executed automatically.
- Git actions default to dry-run.
- Remote pushes and pull requests require explicit configuration and authorization.
- Uploaded files must be restricted by size and type.
- Neo4j queries must be parameterized.
- Generated artifacts and local service data are ignored by Git.

## License

No license has been selected yet. Add a license before distributing or reusing the project outside the intended hackathon context.
