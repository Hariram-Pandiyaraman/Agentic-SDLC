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
