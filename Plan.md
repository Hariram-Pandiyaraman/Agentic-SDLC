# SDLC Agentic Framework Delivery Plan

## 1. Goal

Build a hackathon-ready proof of concept that accepts one feature requirement and demonstrates traceable artifact generation across the SDLC using Streamlit, FastAPI, LangGraph, Ollama, Neo4j, and pytest.

The PoC is successful when a user can submit a requirement, make decisions at the HITL gates, and view a QA handoff whose contents can be traced back through test, code, story, BRD, and requirement artifacts.

## 2. Delivery Principles

- Build the demonstrable happy path first.
- Keep Ollama and Neo4j behind replaceable service interfaces.
- Make every generative step work with a deterministic fallback.
- Persist each artifact immediately after creation.
- Treat traceability as structured data, not only prose.
- Keep Git remote operations mocked or dry-run by default.
- Use native local processes because Docker is not available in the current environment.

## 3. Implementation Phases

### Phase 0 — Local Prerequisites and Skeleton

**Status:** Complete on 2026-07-29. Python and the API/UI skeleton are ready. Ollama and Neo4j are unavailable locally, so fixture and template fallback mode is enabled.

**Target:** 15–20 minutes

- Confirm Python 3.11 or newer.
- Confirm Ollama is reachable and select an installed model.
- Confirm a Neo4j instance is reachable, or enable fixture mode.
- Create the repository structure and configuration loader.
- Add dependencies and `.env.example`.
- Add API and Streamlit health pages.

**Exit criteria**

- FastAPI and Streamlit start locally.
- Configuration validation produces actionable errors.
- `/health` reports API, Ollama, Neo4j, and fallback status.

### Phase 1 — Schemas, Storage, and Traceability

**Status:** Complete on 2026-07-29. The default offline path uses fixture context and JSON lineage; Neo4j constraints and seed support are ready for a future server.

**Target:** 20–25 minutes

- Define Pydantic models for requirements, context, BRD metadata, backlog, test mapping, defects, approvals, and artifacts.
- Implement the per-run artifact directory and manifest.
- Implement stable ID generation and source-artifact references.
- Create the Neo4j schema/constraints and seed mock context.
- Add fixture-backed context and lineage stores.

**Exit criteria**

- A sample normalized requirement validates.
- An artifact can be saved, listed, and linked to its source.
- Context retrieval works through Neo4j or fixtures.

### Phase 2 — LangGraph Workflow and HITL

**Status:** Complete on 2026-07-29. The workflow uses LangGraph interrupts and in-memory checkpoints, persists every agent output, supports all three rejection loops, and completes entirely through deterministic offline agents.

**Target:** 35–45 minutes

- Define the shared workflow state.
- Implement the 11 agent nodes using a common agent result contract.
- Add the scope, BRD, and code-plan interrupts.
- Add checkpointing and resume commands.
- Implement bounded retries and deterministic fallbacks.

**Exit criteria**

- A fixture requirement traverses every node.
- The workflow pauses and resumes at all approval gates.
- Every node writes a manifest entry.

### Phase 3 — Ollama Prompts and Generated Artifacts

**Status:** Complete on 2026-07-29. All generative stages use versioned structured prompts, schema validation, one repair attempt, and deterministic fallbacks with manifest metadata. Ollama remains opt-in because it is not installed locally.

**Target:** 30–40 minutes

- Add shared system constraints for structured, traceable output.
- Add focused prompts for intake, context ranking, clarification, BRD, stories, planning, code, review, sanity, and release.
- Validate structured output and perform one repair attempt.
- Add template fallbacks for each prompt.
- Ensure criteria IDs appear in code comments, tests, findings, and handoff documents.

**Exit criteria**

- Ollama can complete the sample run.
- Disabling Ollama still completes the run using fallbacks.
- All acceptance criteria have implementation and test mappings or an explicit gap.

### Phase 4 — API and Streamlit Experience

**Status:** Complete on 2026-07-29. FastAPI exposes the full run lifecycle and artifact downloads, while Streamlit provides requirement submission, progress, HITL decisions, versioned artifact review, lineage visualization, and ZIP export.

**Target:** 30–40 minutes

- Implement run, status, resume, artifact, and lineage endpoints.
- Add a Streamlit requirement submission page.
- Add workflow progress and approval panels.
- Add artifact tabs and a compact lineage visualization.
- Add artifact download/export.

**Exit criteria**

- The complete flow can be operated without a terminal after startup.
- Approval comments produce new artifact versions.
- Final artifacts can be inspected and downloaded.

### Phase 5 — Review, Tests, and Demo Hardening

**Status:** Complete on 2026-07-29. The seeded offline demo, failed-sanity defect branch, handoff-readiness validator, agent generation contracts, API/UI native startup, and full regression suite are validated. The Ollama path is contract-tested because the Ollama binary is unavailable locally.

**Target:** 20–30 minutes

- Add unit tests for schemas, fallbacks, IDs, and artifact storage.
- Add agent contract tests with mocked LLM responses.
- Add workflow tests for approval, rejection, fallback, and defect branches.
- Add API smoke tests.
- Prepare a seeded sample requirement and expected demo narrative.
- Verify native startup instructions from a clean shell.

**Exit criteria**

- Critical tests pass with `pytest`.
- The demo works with Ollama, and also in deterministic fallback mode.
- A failed sanity check creates a structured defect and still produces a qualified QA handoff.

## 4. Priority Backlog

### Must Have

- Text requirement intake.
- Typed workflow state and artifacts.
- Eleven named agent responsibilities.
- Three architect approval gates.
- BRD, backlog, sprint plan, code plan, implementation stub, unit-test mapping, review, sanity result, defects, release notes, and QA handoff.
- Artifact lineage stored in Neo4j or a local fallback.
- Streamlit UI and FastAPI boundary.
- Ollama generation and deterministic fallback.
- pytest coverage for the critical workflow.

### Should Have

- File upload for `.txt` and `.md`.
- Mermaid or network visualization of lineage.
- Artifact export as a ZIP archive.
- Configurable model and prompt settings.
- Local Git branch and commit support behind an explicit flag.

### Could Have

- Simple `.csv`/`.xlsx` requirement adapter.
- Simulated pull-request response.
- Run comparison and artifact version diff.
- Token/latency dashboard.
- Dockerfiles and Compose configuration validated in CI or another machine.

### Won't Have in the PoC

- Autonomous remote repository mutation.
- Live Jira/Azure DevOps integration.
- Production access control.
- General diagram OCR or complex document understanding.
- Multi-user scaling.

## 5. Test Strategy

| Test level | Scope | Tooling |
|---|---|---|
| Unit | Schemas, IDs, prompt parsing, fallback templates, artifact store | pytest |
| Contract | Each agent returns its declared output shape and traceability fields | pytest, mocked Ollama |
| Integration | Neo4j queries, Ollama gateway, API routes | pytest, test fixtures |
| Workflow | Happy path, rejection loops, model failure, failed sanity checks | pytest, LangGraph test graph |
| UI smoke | Page starts and critical API calls are wired | Streamlit AppTest or a lightweight manual checklist |

Minimum critical scenarios:

1. Valid text requirement completes the happy path.
2. Scope rejection returns to clarification and preserves the earlier version.
3. BRD rejection generates a revised BRD.
4. Code-plan rejection prevents implementation.
5. Ollama timeout activates a visible fallback.
6. Neo4j failure uses fixture context and local lineage.
7. Failed test creates a defect linked to a test result and acceptance criterion.
8. QA handoff lists open risks and traceability gaps.

## 6. Definition of Done

- The selected stack and setup are documented.
- The sample requirement completes end to end.
- HITL decisions are captured with timestamp and comments.
- All required artifacts are versioned and downloadable.
- Every story and generated code/test artifact links to acceptance criteria.
- The final QA handoff states what changed, what was tested, what failed, and remaining risks.
- The knowledge graph or fallback lineage contains the complete run.
- The PoC runs natively without Docker.
- Critical automated tests pass.
- Known limitations and fallback behavior are visible.

## 7. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Local model is slow or unavailable | Demo stalls | Low temperature, small configurable model, timeout, deterministic fallback |
| Ollama emits invalid JSON | Agent output fails validation | Schema prompting, one repair pass, fallback template |
| Neo4j is unavailable | Context and lineage fail | Fixture context provider and local `lineage.json` |
| Scope exceeds hackathon time | Incomplete demo | Implement one golden path and mock external integrations |
| Generated code is unsafe | Local machine risk | Generate into an isolated directory and never execute arbitrary commands |
| Git agent mutates unintended state | Repository damage | Dry-run default and allow-listed, explicit local actions |
| Artifacts lose traceability | Core value is not proven | Stable IDs, manifest validation, traceability completeness check |

## 8. Suggested Demo Script

1. Start FastAPI and Streamlit; show service health.
2. Submit the sample feature requirement.
3. Show normalized requirements and retrieved prior context.
4. Answer one clarification and approve scope.
5. Review and approve the versioned BRD.
6. Show generated stories, Given-When-Then criteria, and sprint plan.
7. Review and approve the code plan.
8. Show the implementation stub and unit-test mapping.
9. Show review findings and a simulated failed sanity check.
10. Open the linked defect and final QA handoff.
11. Display the lineage graph from requirement through release.
12. Briefly demonstrate that fallback mode can complete the flow without the model.

## 9. Post-PoC Roadmap

1. Replace fixture adapters with enterprise document, Jira, Git, and CI integrations.
2. Add authentication, authorization, audit retention, and policy enforcement.
3. Introduce retrieval quality evaluation and graph ranking.
4. Add sandboxed code execution and real test runners.
5. Add observability, prompt/version evaluation, cost/latency metrics, and run comparison.
6. Package and validate Docker images, then add a production deployment target.

---

# SDLC Agentic Framework 0.2.1 Release Plan

> The completed 0.2.0 delivery plan above is retained unchanged. This is the additive plan for 0.2.1.

## 1. Readiness Decision

**Decision:** Go to start 0.2.1 development; not yet ready to release 0.2.1.

The 0.2.0 baseline is stable enough to extend: the repository is at the `0.2.0` commit and all 27 automated tests pass when pytest uses a workspace-local temporary directory. The largest product gap is the functional but dated single-page Streamlit UI. The second gap is persistence: artifacts and lineage are file-backed, with optional Neo4j, and there is no relational database abstraction.

0.2.1 is ready to release only when the redesigned UI makes the workflow easier to operate and understand, and the critical workflow behaves consistently with SQLite, SQL Server, and MySQL.

## 2. Release Goal

Turn the 0.2.0 proof of concept into a modern, durable operator experience without breaking its traceability or offline-first behavior.

The release will:

- Replace the current long Streamlit page with a polished application shell and task-focused screens.
- Make active approvals, progress, risks, and traceability understandable at a glance.
- Use SQLite as the zero-setup relational default.
- Support SQL Server and MySQL as configurable shared backends.
- Use MySQL Workbench for MySQL administration and manual acceptance checks.
- Keep Neo4j optional for native graph retrieval and visualization.
- Preserve deterministic generation, HITL gates, artifact versioning, and ZIP export.

## 3. Product and Architecture Decisions

### 3.1 UI direction

- Keep Streamlit for 0.2.1 to control release scope, but rebuild the information architecture and visual system rather than applying isolated styling fixes.
- Use a persistent application shell: branded header, left navigation, compact environment indicator, and a clear primary action.
- Split the experience into Dashboard, New Run, Run Workspace, Approvals, Artifacts, and Settings/About views.
- Make the Run Workspace the core screen with Overview, Artifacts, Traceability, Activity, and Diagnostics tabs.
- Replace the 11 text progress labels with a responsive workflow stepper showing complete, active, blocked, failed, fallback, and pending states.
- Present approval requests as a focused review workspace with artifact preview, version context, decision history, required comments, and a sticky action area.
- Render structured artifacts as readable sections and tables by default, with raw JSON available as a secondary developer view.
- Provide search, filtering, empty states, skeleton/loading states, clear errors, and confirmation feedback.
- Define reusable design tokens and components; avoid scattered one-off CSS.

### 3.2 Database roles

| Technology | 0.2.1 role |
|---|---|
| SQLite | Default local/demo relational database, created automatically |
| SQL Server | Supported shared/enterprise relational database |
| MySQL | Supported shared relational database |
| MySQL Workbench | Client for schema inspection and manual MySQL verification, not the database engine |
| Neo4j | Optional knowledge graph and lineage projection |
| Filesystem | Export compatibility and 0.2.0 migration source, not the sole metadata authority |

### 3.3 Persistence boundary

- Introduce repository interfaces for runs, artifacts, approvals, fallback events, workflow snapshots, and lineage.
- Implement the interfaces with SQLAlchemy 2.x; workflow, API, and UI code must not branch on database vendor.
- Use Alembic as the only supported schema migration mechanism.
- Store authoritative run/artifact metadata and durable workflow snapshots in the relational database.
- Store artifact content durably while continuing to materialize files for downloads and ZIP export.
- Store lineage relationally on every backend and optionally project it to Neo4j.
- Select the backend with one `DATABASE_URL`; default to project-local SQLite.
- Use `pyodbc` for SQL Server and a maintained SQLAlchemy-compatible MySQL driver.
- Redact connection credentials from health responses, logs, manifests, and errors.

## 4. Delivery Phases

### Phase 0 — Baseline and UX foundation

**Status:** Complete (2026-08-01).

- Preserve the tested 0.2.0 baseline and add an explicit application version.
- Make pytest temp/cache paths workspace-local on Windows.
- Capture current API response shapes and artifact behavior in regression tests.
- Inventory the existing UI states: first use, running, awaiting approval, rejected, failed, fallback, and complete.
- Create a compact visual specification covering typography, color, spacing, elevation, borders, icons, state colors, and responsive breakpoints.
- Define reusable UI components before rebuilding screens.

**Exit criteria**

- The 0.2.0 regression suite remains green.
- Every current workflow state has a designed UI treatment.
- The visual system meets WCAG AA color contrast for normal text and interactive states.

### Phase 1 — Modern application shell and dashboard

**Status:** Complete (2026-08-04).

- Add branded navigation and a responsive, wide-screen-first application shell.
- Build a dashboard with recent runs, status summary cards, pending approvals, failure/fallback indicators, and a prominent New Run action.
- Add run search and filters for status, date, and requirement title.
- Redesign requirement intake as a guided form with inline validation, file preview, advanced options in progressive disclosure, and a clear success transition.
- Move raw service diagnostics out of the main workflow and into a compact status popover plus Diagnostics view.

**Exit criteria**

- A first-time user can create or reopen a run without instructions.
- Dashboard and intake layouts work at desktop and tablet widths without horizontal overflow.
- Loading, empty, validation, API-unavailable, and success states are intentionally designed and tested.

### Phase 2 — Run workspace, approvals, and artifact experience

**Status:** Complete (2026-08-04).

- Build a run header with title, status, current stage, elapsed/updated time, fallback count, and primary next action.
- Add the visual workflow stepper and an activity timeline for agent results and HITL decisions.
- Build a dedicated approval experience with side-by-side review context where space permits.
- Add artifact cards/table views, type and producer filters, version history, metadata drawer, formatted preview, raw view, and per-artifact download.
- Add readable renderers for BRD, backlog/stories, plans, tests, defects, release notes, and QA handoff.
- Improve lineage with zoomable visual grouping, relationship legend, node details, and a list/table fallback.
- Keep complete-run export available from a consistent action menu.

**Exit criteria**

- Current stage and required user action are identifiable within five seconds.
- Approve/reject actions cannot target the wrong artifact version and rejection requires a comment.
- Structured artifacts are usable without reading raw JSON.
- Keyboard navigation, visible focus, labels, and screen-reader-friendly status text cover critical actions.

### Phase 3 — Relational foundation and SQLite vertical slice

- Add SQLAlchemy models, Alembic configuration, repositories, and transaction handling.
- Create tables for runs, artifacts, artifact versions, artifact sources, approvals, fallback events, workflow snapshots, lineage nodes, and lineage edges.
- Preserve stable IDs, checksums, revision rules, source links, and immutable decision history.
- Wire SQLite as the default and enable foreign keys, bounded busy timeout, and safe short transactions.
- Update API queries needed by the dashboard, filters, activity timeline, and pending-approval view.

**Exit criteria**

- A fresh SQLite database upgrades to the latest schema by a documented command.
- The happy path and all rejection loops survive API/process restart.
- Existing API behavior and the redesigned UI pass against SQLite.
- Injected write failures roll back without partial records.

### Phase 4 — SQL Server and MySQL support

- Validate Alembic migrations and the critical integration suite on the available SQL Server instance.
- Handle SQL Server differences for Unicode text, timestamps, booleans, indexes, identity behavior, and large payloads.
- Validate migrations and the critical integration suite on the available MySQL instance.
- Use `utf8mb4` and handle MySQL differences for text size, JSON, timestamps, booleans, index length, collation, and transaction isolation.
- Add actionable readiness checks for missing drivers, authentication, connectivity, database selection, and pending migrations.
- Document least-privilege setup for both servers.
- Provide MySQL Workbench setup steps and checked-in verification queries.

**Exit criteria**

- Empty SQL Server and MySQL databases migrate successfully.
- The end-to-end demo passes on both backends with no application-code switch beyond configuration.
- Unicode, large artifacts, rollback, restart/resume, concurrent revision creation, and export pass.
- Workbench can inspect runs, artifact versions, approvals, and lineage using documented queries.

### Phase 5 — 0.2.0 migration and compatibility

- Build an idempotent import command for 0.2.0 run directories, manifests, artifact files, fallback events, and lineage JSON.
- Support dry-run, one-run, and all-runs modes.
- Verify checksums and report corrupt, missing, duplicate, or unsupported records without silent data loss.
- Record import provenance and keep the original 0.2.0 directories untouched.

**Exit criteria**

- A copied 0.2.0 artifact set imports into all three databases with matching counts and checksums.
- Re-import creates no duplicates.
- Failed imports roll back and produce an actionable report.
- Imported runs are visible in the new dashboard and remain viewable/exportable.

### Phase 6 — Polish, validation, and release

- Add component-level UI tests where practical and end-to-end tests for the critical user journeys.
- Run usability checks with at least one user unfamiliar with the implementation and address high-friction findings.
- Measure common-screen render time and avoid unnecessary full-page API calls/reruns.
- Validate empty, large, slow, error, fallback, and long-content states.
- Run the complete database test matrix.
- Update README, Architecture.md, `.env.example`, screenshots, demo script, migration guide, troubleshooting, and release notes.

**Exit criteria**

- Critical UI journeys pass at desktop and tablet widths.
- No high-severity usability, accessibility, security, migration, data-loss, or traceability defects remain.
- The three-backend matrix is green.
- A 0.2.0 user can upgrade or roll back without losing original artifacts.

## 5. UI Scope and Acceptance Journeys

### Required screens

| Screen | Primary purpose | Required content |
|---|---|---|
| Dashboard | Resume work and spot exceptions | Recent runs, status counts, pending approvals, failures/fallbacks, search/filter, New Run |
| New Run | Submit a high-quality requirement | Title, requirement editor/upload, preview, validation, advanced simulation options |
| Run Overview | Understand state and next action | Run summary, visual stepper, current action, metrics, risks, activity timeline |
| Approval Review | Make a safe HITL decision | Exact artifact/version, formatted preview, upstream context, decision history, comment, approve/reject |
| Artifacts | Explore delivery output | Group/filter/search, readable preview, versions, metadata, raw view, download/export |
| Traceability | Inspect coverage and lineage | Interactive graph, legend, details, table fallback, gaps and linked artifacts |
| Diagnostics | Troubleshoot without cluttering the workflow | API/model/database/Neo4j state, fallback events, safe error detail, refresh |

### Critical user journeys

1. Create a run from pasted text and understand what will happen next.
2. Leave the application, return, find the run, and resume it.
3. Identify a pending approval from the dashboard and make a version-safe decision.
4. Understand which agents completed, which stage is active, and whether fallback behavior occurred.
5. Read BRD, stories, tests, defects, and QA handoff without opening raw JSON.
6. Trace an acceptance criterion from requirement through implementation, test, and release.
7. Diagnose an unavailable API, model, database, or Neo4j connection from one place.
8. Download one artifact or export the complete run.

### UX quality bar

- No critical action depends on color alone.
- Keyboard focus is visible and follows a logical order.
- Every input has a persistent label; errors appear next to the affected control.
- Destructive or consequential decisions show the exact target and outcome.
- Status terminology is consistent across dashboard, workspace, approvals, and API responses.
- Long artifact content remains readable with sensible line length, headings, tables, and sticky context where useful.
- Desktop is the primary operating layout; tablet is fully supported; phone widths provide a usable read/review experience.
- Common pages show useful structure quickly and avoid blocking the entire screen for secondary data.

## 6. Proposed Relational Data Model

| Table | Purpose | Key constraints |
|---|---|---|
| `runs` | Run identity, title, workflow status, current gate, timestamps | Unique run ID; constrained status |
| `artifacts` | Stable artifact identity and type within a run | Unique `(run_id, artifact_id)` |
| `artifact_versions` | Immutable content, checksum, producer, model metadata, approval state | Unique `(artifact_id, version)`; positive version |
| `artifact_sources` | Version-aware derivation links | Valid source and target; no duplicate link |
| `approvals` | HITL gate, exact artifact version, decision, comment, actor, timestamp | Constrained gate/decision; immutable history |
| `fallback_events` | Model, context, or projection fallback audit | Run foreign key and timestamp |
| `workflow_snapshots` | Durable resume state and monotonic checkpoint sequence | Unique `(run_id, sequence)` |
| `lineage_nodes` | Queryable artifact nodes | Unique artifact reference |
| `lineage_edges` | Typed traceability relationships | Allowed type; unique logical edge |
| `schema_metadata` | Import/application metadata not owned by Alembic | Unique metadata key |

Large structured fields must use portable serialization contracts. Vendor-native JSON capabilities may be optional optimizations only after portable behavior passes on all three backends.

## 7. Test Matrix

### UI and user-journey matrix

| Scenario | Automated | Manual acceptance |
|---|---:|---:|
| New run with pasted text and uploaded Markdown | Required | Required |
| Dashboard search, filter, reopen, and empty state | Required | Required |
| Visual progress and fallback/error states | Required | Required |
| Approve and reject exact artifact versions | Required | Required |
| Formatted artifact views and raw fallback | Required | Required |
| Version history and downloads | Required | Required |
| Traceability graph and accessible table fallback | Required | Required |
| API/database/model unavailable states | Required | Required |
| Keyboard-only critical journey | Best feasible | Required |
| Desktop and tablet responsive layouts | Best feasible | Required |
| Contrast, labels, focus, and status semantics | Required checks | Required |

### Database matrix

| Scenario | SQLite | SQL Server | MySQL |
|---|---:|---:|---:|
| Empty database migration | Required | Required | Required |
| Happy-path workflow | Required | Required | Required |
| All three rejection loops | Required | Required | Required |
| Restart/resume at every HITL gate | Required | Required | Required |
| Failed sanity and linked defect | Required | Required | Required |
| Concurrent artifact revision attempt | Required | Required | Required |
| Transaction rollback on injected failure | Required | Required | Required |
| Unicode and large artifact round-trip | Required | Required | Required |
| 0.2.0 import and idempotent re-import | Required | Required | Required |
| API list/read/filter/export parity | Required | Required | Required |
| Neo4j unavailable with relational lineage intact | Required | Required | Required |
| Credential redaction and safe health output | Required | Required | Required |

SQLite tests run in the normal local/CI suite. SQL Server and MySQL tests may be marker-gated during routine development, but both are mandatory for a release candidate. MySQL Workbench checks complement, and do not replace, automated MySQL tests.

## 8. Definition of Done for 0.2.1

- The modern application shell, dashboard, guided intake, run workspace, approvals, artifacts, traceability, and diagnostics views are complete.
- Critical actions and status are clear without reading raw JSON or service responses.
- Required responsive and accessibility checks pass.
- `DATABASE_URL` selects SQLite, SQL Server, or MySQL without application-code changes.
- SQLite remains a zero-setup local path and all schema changes use Alembic.
- Workflow state and HITL decisions survive application restart.
- Artifact IDs, versions, checksums, sources, approvals, and lineage retain 0.2.0 semantics.
- Existing 0.2.0 runs can be dry-run validated and imported idempotently.
- Filesystem downloads and ZIP exports remain available.
- Neo4j remains optional and is not a single point of failure.
- Secrets are redacted and least-privilege setup is documented.
- UI and three-database release matrices pass.
- README, Architecture.md, `.env.example`, screenshots, demo, migration guide, and release notes match shipped behavior.

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Streamlit reruns and layout limits constrain the desired UX | UI still feels like a prototype | Component boundaries, session-state discipline, cached reads, early UX spike; record a post-0.2.1 SPA decision if hard limits remain |
| Styling becomes scattered and brittle | Inconsistent or hard-to-maintain UI | Central design tokens and reusable render components; minimal targeted CSS |
| UI polish expands without improving workflows | Release delay | Prioritize the eight acceptance journeys and measurable usability gates |
| Vendor SQL differences leak into services | Inconsistent behavior | Repository boundary, SQLAlchemy portability tests, isolated adapters |
| Windows database drivers are missing or mismatched | Server backends cannot start | Preflight checks, supported driver versions, actionable diagnostics |
| Concurrent artifact revisions collide | Lost or duplicate versions | Uniqueness constraint, transaction, bounded retry |
| Large artifacts exceed vendor limits | Failed/truncated persistence | Unindexed large-text content, size tests, explicit errors |
| Migration damages 0.2.0 runs | Data loss | Dry-run, checksums, idempotency, rollback, preserve source files |
| SQLite locking appears under concurrency | Intermittent local failures | Short transactions, busy timeout/WAL where supported, document limits |
| MySQL collation changes ID comparison | Broken uniqueness/traceability | Explicit `utf8mb4` charset/collation and case-sensitivity tests |
| Credentials leak through diagnostics | Security exposure | Central URL redaction and log/API tests |
| Relational and Neo4j lineage diverge | Misleading graph | Relational data is authoritative; idempotent Neo4j projection with visible status |

## 10. Recommended Implementation Order

1. Stabilize the baseline test environment and lock API/behavior regression tests.
2. Prototype the visual system, shell, dashboard, and one end-to-end run workspace journey using current APIs.
3. Complete approval and formatted artifact experiences; validate the UX direction early.
4. Add SQLAlchemy repositories, Alembic, and the SQLite vertical slice.
5. Add durable snapshots plus the dashboard/filter APIs and connect the full UI.
6. Validate SQL Server, then MySQL and the MySQL Workbench workflow.
7. Add the idempotent 0.2.0 importer.
8. Run usability/accessibility checks and the full three-backend release matrix.
9. Publish 0.2.1 documentation and release notes.

## 11. Go/No-Go Checklist

### Ready to start development

- [x] 0.2.0 commit is identifiable.
- [x] Baseline suite passes with an accessible temp path (27 tests).
- [x] The current UI states and primary shortcomings are understood.
- [x] SQLite, SQL Server, MySQL, MySQL Workbench, and Neo4j roles are defined.

### Required before 0.2.1 release

- [ ] Modern shell, dashboard, intake, run workspace, and diagnostics are complete.
- [ ] Approval, artifact, and traceability experiences meet the UX quality bar.
- [ ] Critical responsive, keyboard, contrast, label, focus, and error-state checks pass.
- [ ] Relational repositories and schema are implemented.
- [ ] SQLite critical workflows pass.
- [ ] SQL Server integration and migration tests pass.
- [ ] MySQL integration, migration tests, and Workbench checks pass.
- [ ] Restart/resume and concurrency behavior pass on all backends.
- [ ] 0.2.0 import is checksum-verified, idempotent, and documented.
- [ ] Credential redaction and outage behavior are verified.
- [ ] Documentation, screenshots, demo, and 0.2.1 release notes are complete.
- [ ] Full UI and database release matrices are green with no open high-severity defects.
