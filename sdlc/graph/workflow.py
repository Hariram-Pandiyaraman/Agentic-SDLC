"""Checkpointed 11-agent LangGraph workflow with three HITL gates."""

from typing import Any

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from sdlc.agents import deterministic
from sdlc.models import (
    AgentResult,
    ApprovalRecord,
    Backlog,
    ClarificationOutput,
    ContextRankingOutput,
    ContextPack,
    GateDecision,
    ImplementationOutput,
    MarkdownOutput,
    NormalizedRequirement,
    ReleaseOutput,
    ReviewOutput,
    SanityOutput,
    SprintPlanOutput,
    WorkflowState,
)
from sdlc.models.common import ApprovalStatus
from sdlc.config import get_settings
from sdlc.services.artifact_store import ArtifactStore
from sdlc.services.context import FixtureContextProvider
from sdlc.services.generation import GenerationResult, OllamaGenerationService
from sdlc.services.ids import next_artifact_id
from sdlc.services.lineage import JsonLineageStore

AGENT_NAMES = {
    "Intake Agent",
    "Context Agent",
    "Clarification Agent",
    "BRD Agent",
    "Story Agent",
    "Plan Agent",
    "Code Agent",
    "Git Agent",
    "Review Agent",
    "Sanity Agent",
    "Release Agent",
}


class WorkflowNodes:
    def __init__(
        self,
        store: ArtifactStore,
        generator: OllamaGenerationService | None = None,
    ) -> None:
        self.store = store
        self.context_provider = FixtureContextProvider()
        self.generator = generator or OllamaGenerationService(get_settings())

    @staticmethod
    def _ids(state: WorkflowState) -> dict[str, list[str]]:
        return {key: list(value) for key, value in state.get("artifact_ids", {}).items()}

    def _complete(
        self,
        state: WorkflowState,
        agent_name: str,
        summary: str,
        artifact_type_to_ids: dict[str, list[str]],
        *,
        attempts: int = 1,
        fallback_used: bool = False,
        updates: dict[str, Any] | None = None,
    ) -> dict:
        ids = self._ids(state)
        output_ids: list[str] = []
        for artifact_type, artifact_ids in artifact_type_to_ids.items():
            ids.setdefault(artifact_type, []).extend(artifact_ids)
            output_ids.extend(artifact_ids)
        results = list(state.get("agent_results", []))
        results.append(
            AgentResult(
                agent_name=agent_name,
                status="completed_with_fallback" if fallback_used else "completed",
                summary=summary,
                output_artifact_ids=output_ids,
                attempts=attempts,
                fallback_used=fallback_used,
            ).model_dump(mode="json")
        )
        response = {
            "current_node": agent_name,
            "status": "running",
            "artifact_ids": ids,
            "agent_results": results,
        }
        response.update(updates or {})
        return response

    def intake(self, state: WorkflowState) -> dict:
        outcome = self.generator.generate(
            "intake",
            NormalizedRequirement,
            {
                "requirement_id": "REQ-001",
                "title": state["requirement_title"],
                "raw_requirement": state["raw_requirement"],
            },
            lambda: deterministic.normalized_requirement(
                state["raw_requirement"], state["requirement_title"]
            ),
        )
        requirement = outcome.value
        record = self.store.save_artifact(
            state["run_id"],
            "requirement",
            requirement,
            "Intake Agent",
            model_metadata=outcome.metadata(),
        )
        fallback_events = self._track_generation(state, "Intake Agent", outcome)
        return self._complete(
            state,
            "Intake Agent",
            "Normalized the raw feature requirement.",
            {"requirement": [record.artifact_id]},
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={
                "normalized_requirement": requirement.model_dump(mode="json"),
                "fallback_events": fallback_events,
            },
        )

    def context(self, state: WorkflowState) -> dict:
        requirement = NormalizedRequirement.model_validate(state["normalized_requirement"])
        context_pack = self.context_provider.retrieve(requirement)
        ranking = self.generator.generate(
            "context_ranking",
            ContextRankingOutput,
            {
                "requirement": requirement.model_dump(mode="json"),
                "candidates": [
                    item.model_dump(mode="json") for item in context_pack.items
                ],
            },
            lambda: ContextRankingOutput(
                ordered_artifact_ids=[item.artifact_id for item in context_pack.items],
                rationale={},
            ),
        )
        by_id = {item.artifact_id: item for item in context_pack.items}
        ordered_ids = [
            artifact_id
            for artifact_id in ranking.value.ordered_artifact_ids
            if artifact_id in by_id
        ]
        ordered_ids.extend(
            artifact_id for artifact_id in by_id if artifact_id not in ordered_ids
        )
        context_pack = context_pack.model_copy(
            update={"items": [by_id[artifact_id] for artifact_id in ordered_ids]}
        )
        record = self.store.save_artifact(
            state["run_id"],
            "context_pack",
            context_pack,
            "Context Agent",
            source_artifact_ids=[self._latest(state, "requirement")],
            model_metadata=ranking.metadata(),
        )
        fallback_events = self._track_generation(state, "Context Agent", ranking)
        return self._complete(
            state,
            "Context Agent",
            f"Retrieved {len(context_pack.items)} related context items.",
            {"context_pack": [record.artifact_id]},
            attempts=ranking.attempts,
            fallback_used=ranking.fallback_used,
            updates={
                "context_pack": context_pack.model_dump(mode="json"),
                "fallback_events": fallback_events,
            },
        )

    def clarification(self, state: WorkflowState) -> dict:
        requirement = NormalizedRequirement.model_validate(state["normalized_requirement"])
        outcome = self.generator.generate(
            "clarification",
            ClarificationOutput,
            {
                "requirement": requirement.model_dump(mode="json"),
                "context_pack": state["context_pack"],
                "revision_feedback": state.get("gate_feedback"),
            },
            lambda: ClarificationOutput.model_validate(
                deterministic.clarification(requirement, state.get("gate_feedback"))
            ),
        )
        content = outcome.value.model_dump(mode="json")
        record = self.store.save_artifact(
            state["run_id"],
            "clarification",
            content,
            "Clarification Agent",
            source_artifact_ids=[
                self._latest(state, "requirement"),
                self._latest(state, "context_pack"),
            ],
            model_metadata=outcome.metadata(),
        )
        fallback_events = self._track_generation(state, "Clarification Agent", outcome)
        return self._complete(
            state,
            "Clarification Agent",
            "Registered assumptions and resolved the PoC clarification.",
            {"clarification": [record.artifact_id]},
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={
                "scope_approved": False,
                "gate_feedback": {},
                "fallback_events": fallback_events,
            },
        )

    def brd(self, state: WorkflowState) -> dict:
        requirement = NormalizedRequirement.model_validate(state["normalized_requirement"])
        outcome = self.generator.generate(
            "brd",
            MarkdownOutput,
            {
                "requirement": requirement.model_dump(mode="json"),
                "context_pack": state["context_pack"],
                "clarification_artifact_id": self._latest(state, "clarification"),
                "revision_feedback": state.get("gate_feedback"),
            },
            lambda: MarkdownOutput(
                markdown=deterministic.brd_markdown(
                    requirement, state.get("gate_feedback")
                )
            ),
        )
        content = outcome.value.markdown
        existing = state.get("artifact_ids", {}).get("brd", [])
        artifact_id = existing[-1] if existing else None
        record = self.store.save_artifact(
            state["run_id"],
            "brd",
            content,
            "BRD Agent",
            source_artifact_ids=[
                self._latest(state, "requirement"),
                self._latest(state, "clarification"),
            ],
            artifact_id=artifact_id,
            approval_status=ApprovalStatus.PENDING,
            confidence=0.85,
            model_metadata=outcome.metadata(),
        )
        fallback_events = self._track_generation(state, "BRD Agent", outcome)
        return self._complete(
            state,
            "BRD Agent",
            f"Generated BRD version {record.version}.",
            {"brd": [record.artifact_id]},
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={
                "brd_approved": False,
                "gate_feedback": {},
                "fallback_events": fallback_events,
            },
        )

    def story(self, state: WorkflowState) -> dict:
        brd_id = self._latest(state, "brd")
        outcome = self.generator.generate(
            "stories",
            Backlog,
            {
                "brd_id": brd_id,
                "brd_markdown": self.store.read_artifact(state["run_id"], brd_id),
                "required_acceptance_criterion_ids": ["AC-001"],
            },
            lambda: deterministic.backlog(brd_id),
        )
        backlog = outcome.value
        record = self.store.save_artifact(
            state["run_id"],
            "backlog",
            backlog,
            "Story Agent",
            source_artifact_ids=[brd_id],
            model_metadata=outcome.metadata(),
        )
        fallback_events = self._track_generation(state, "Story Agent", outcome)
        return self._complete(
            state,
            "Story Agent",
            "Created one epic, one story, subtasks, and Given-When-Then criteria.",
            {"backlog": [record.artifact_id]},
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={
                "backlog": backlog.model_dump(mode="json"),
                "fallback_events": fallback_events,
            },
        )

    def plan(self, state: WorkflowState) -> dict:
        fallback_markdown = """# Sprint Plan

1. Validate the approved BRD and acceptance criteria.
2. Implement the checkpointed workflow and deterministic artifacts.
3. Run review and sanity validation.
4. Package the QA handoff and lineage.

Critical path: approved BRD → approved code plan → sanity result → QA handoff.
"""
        outcome = self.generator.generate(
            "planning",
            SprintPlanOutput,
            {
                "backlog": state["backlog"],
                "required_acceptance_criterion_ids": ["AC-001"],
            },
            lambda: SprintPlanOutput(
                markdown=fallback_markdown,
                critical_path=["BRD approval", "Code-plan approval", "Sanity", "QA handoff"],
                risks=["Local model and graph services may be unavailable."],
            ),
        )
        record = self.store.save_artifact(
            state["run_id"],
            "sprint_plan",
            outcome.value.markdown,
            "Plan Agent",
            source_artifact_ids=[self._latest(state, "backlog")],
            model_metadata=outcome.metadata(),
        )
        fallback_events = self._track_generation(state, "Plan Agent", outcome)
        return self._complete(
            state,
            "Plan Agent",
            "Sequenced the PoC implementation and critical path.",
            {"sprint_plan": [record.artifact_id]},
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={"fallback_events": fallback_events},
        )

    def code_plan(self, state: WorkflowState) -> dict:
        fallback_markdown = """# Code Plan

- Define a typed LangGraph state.
- Add eleven agent responsibilities.
- Interrupt at scope, BRD, and code-plan gates.
- Checkpoint by run ID.
- Persist every completed agent artifact.
- Map generated tests to AC-001.
"""
        outcome = self.generator.generate(
            "code_plan",
            MarkdownOutput,
            {
                "backlog": state["backlog"],
                "sprint_plan_artifact_id": self._latest(state, "sprint_plan"),
                "required_acceptance_criterion_ids": ["AC-001"],
                "revision_feedback": state.get("gate_feedback"),
            },
            lambda: MarkdownOutput(markdown=fallback_markdown),
        )
        existing = state.get("artifact_ids", {}).get("code_plan", [])
        artifact_id = existing[-1] if existing else None
        record = self.store.save_artifact(
            state["run_id"],
            "code_plan",
            outcome.value.markdown,
            "Code Agent",
            source_artifact_ids=[
                self._latest(state, "backlog"),
                self._latest(state, "sprint_plan"),
            ],
            artifact_id=artifact_id,
            approval_status=ApprovalStatus.PENDING,
            model_metadata=outcome.metadata(),
        )
        fallback_events = self._track_generation(state, "Code Agent", outcome)
        return self._complete(
            state,
            "Code Agent",
            f"Generated code-plan version {record.version}.",
            {"code_plan": [record.artifact_id]},
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={
                "code_plan_approved": False,
                "gate_feedback": {},
                "fallback_events": fallback_events,
            },
        )

    def code_build(self, state: WorkflowState) -> dict:
        fallback_code = ImplementationOutput.model_validate(
            {
                "files": [
                    {
                        "path": "generated/feature_stub.py",
                        "acceptance_criterion_ids": ["AC-001"],
                        "content": (
                        "def build_traceable_handoff(requirement_id: str) -> dict:\n"
                        "    \"\"\"Implementation stub for AC-001.\"\"\"\n"
                        "    return {'requirement_id': requirement_id, 'status': 'ready'}\n"
                        ),
                    }
                ]
            }
        )
        outcome = self.generator.generate(
            "implementation",
            ImplementationOutput,
            {
                "code_plan": self.store.read_artifact(
                    state["run_id"], self._latest(state, "code_plan")
                ),
                "required_acceptance_criterion_ids": ["AC-001"],
            },
            lambda: fallback_code,
        )
        code = outcome.value
        code_record = self.store.save_artifact(
            state["run_id"],
            "code",
            code,
            "Code Agent",
            source_artifact_ids=[
                self._latest(state, "code_plan"),
                self._latest(state, "backlog"),
            ],
            model_metadata=outcome.metadata(),
        )
        mapping = deterministic.test_mapping()
        test_record = self.store.save_artifact(
            state["run_id"],
            "test_case",
            mapping,
            "Code Agent",
            source_artifact_ids=[code_record.artifact_id],
            model_metadata=outcome.metadata(),
        )
        fallback_events = self._track_generation(state, "Code Agent", outcome)
        return self._complete(
            state,
            "Code Agent",
            "Generated an implementation stub and AC-001 test mapping.",
            {
                "code": [code_record.artifact_id],
                "test_case": [test_record.artifact_id],
            },
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={
                "implementation": code.model_dump(mode="json"),
                "fallback_events": fallback_events,
            },
        )

    def git(self, state: WorkflowState) -> dict:
        content = {
            "mode": "dry_run",
            "branch": f"feature/{state['run_id'].lower()}",
            "commands": [
                "git switch -c <branch>",
                "git add <generated-files>",
                "git commit -m 'feat: generate traceable feature stub'",
            ],
            "executed": False,
        }
        record = self.store.save_artifact(
            state["run_id"],
            "git_plan",
            content,
            "Git Agent",
            source_artifact_ids=[self._latest(state, "code")],
        )
        return self._complete(
            state,
            "Git Agent",
            "Prepared dry-run Git operations without mutating the repository.",
            {"git_plan": [record.artifact_id]},
        )

    def review(self, state: WorkflowState) -> dict:
        fallback_review = ReviewOutput.model_validate(
            {
                "criterion_reviews": [
                    {
                        "acceptance_criterion_id": "AC-001",
                        "status": "covered",
                        "finding": "AC-001 appears in implementation metadata, code comments, and tests.",
                        "severity": "info",
                    }
                ],
                "verdict": "approved_for_sanity",
            }
        )
        outcome = self.generator.generate(
            "review",
            ReviewOutput,
            {
                "brd_id": self._latest(state, "brd"),
                "implementation": state["implementation"],
                "test_case_id": self._latest(state, "test_case"),
                "required_acceptance_criterion_ids": ["AC-001"],
            },
            lambda: fallback_review,
        )
        content = outcome.value
        record = self.store.save_artifact(
            state["run_id"],
            "review",
            content,
            "Review Agent",
            source_artifact_ids=[
                self._latest(state, "brd"),
                self._latest(state, "code"),
                self._latest(state, "test_case"),
            ],
            model_metadata=outcome.metadata(),
        )
        fallback_events = self._track_generation(state, "Review Agent", outcome)
        return self._complete(
            state,
            "Review Agent",
            "Reviewed the stub against the BRD and AC-001.",
            {"review": [record.artifact_id]},
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={
                "review": content.model_dump(mode="json"),
                "fallback_events": fallback_events,
            },
        )

    def sanity(self, state: WorkflowState) -> dict:
        failed = state.get("simulate_test_failure", False)
        expected_status = "failed" if failed else "passed"
        outcome = self.generator.generate(
            "sanity",
            SanityOutput,
            {
                "test_case_id": "TC-001",
                "acceptance_criterion_ids": ["AC-001"],
                "deterministic_test_status": expected_status,
                "review": state["review"],
            },
            lambda: SanityOutput(
                acceptance_criterion_ids=["AC-001"],
                status=expected_status,
                summary="Deterministic simulated sanity result.",
            ),
        )
        sanity_output = outcome.value.model_copy(update={"status": expected_status})
        result = {
            "test_result_id": "TR-001",
            "test_case_id": "TC-001",
            **sanity_output.model_dump(mode="json"),
            "simulated": True,
        }
        result_record = self.store.save_artifact(
            state["run_id"],
            "test_result",
            result,
            "Sanity Agent",
            source_artifact_ids=[
                self._latest(state, "test_case"),
                self._latest(state, "review"),
            ],
            model_metadata=outcome.metadata(),
        )
        artifact_map = {"test_result": [result_record.artifact_id]}
        defects: list[dict] = []
        if failed:
            defect = deterministic.defect(result_record.artifact_id)
            defect_record = self.store.save_artifact(
                state["run_id"],
                "defect",
                defect,
                "Sanity Agent",
                source_artifact_ids=[result_record.artifact_id],
                model_metadata=outcome.metadata(),
            )
            artifact_map["defect"] = [defect_record.artifact_id]
            defects.append(defect.model_dump(mode="json"))
        return self._complete(
            state,
            "Sanity Agent",
            "Recorded sanity results and created a defect when required.",
            artifact_map,
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={
                "test_results": [result],
                "defects": defects,
                "fallback_events": self._track_generation(
                    state, "Sanity Agent", outcome
                ),
            },
        )

    def release(self, state: WorkflowState) -> dict:
        test_status = state.get("test_results", [{}])[0].get("status", "unknown")
        fallback_release = f"""# Release Notes

- Run: {state['run_id']}
- Generated a traceable implementation stub for AC-001.
- Sanity status: {test_status}
- Git actions remained in dry-run mode.
"""
        fallback_qa = f"""# QA Handoff

- Requirement: {self._latest(state, 'requirement')}
- BRD: {self._latest(state, 'brd')}
- Acceptance criterion: AC-001
- Code artifact: {self._latest(state, 'code')}
- Test result: {self._latest(state, 'test_result')} ({test_status})
- Open defects: {len(state.get('defects', []))}
"""
        outcome = self.generator.generate(
            "release",
            ReleaseOutput,
            {
                "run_id": state["run_id"],
                "requirement_id": self._latest(state, "requirement"),
                "brd_id": self._latest(state, "brd"),
                "acceptance_criterion_ids": ["AC-001"],
                "code_id": self._latest(state, "code"),
                "test_result_id": self._latest(state, "test_result"),
                "test_status": test_status,
                "defect_ids": state.get("artifact_ids", {}).get("defect", []),
            },
            lambda: ReleaseOutput(
                release_notes_markdown=fallback_release,
                qa_handoff_markdown=fallback_qa,
                open_risks=[] if test_status == "passed" else ["Sanity test failed."],
            ),
        )
        release_output = outcome.value
        if "AC-001" not in release_output.qa_handoff_markdown:
            release_output = release_output.model_copy(
                update={
                    "qa_handoff_markdown": (
                        release_output.qa_handoff_markdown
                        + "\n- Acceptance criteria: AC-001\n"
                    )
                }
            )
        release_record = self.store.save_artifact(
            state["run_id"],
            "release",
            release_output.release_notes_markdown,
            "Release Agent",
            source_artifact_ids=[
                self._latest(state, "code"),
                self._latest(state, "test_result"),
            ],
            model_metadata=outcome.metadata(),
        )
        qa_sources = [release_record.artifact_id, self._latest(state, "test_result")]
        if state.get("artifact_ids", {}).get("defect"):
            qa_sources.append(self._latest(state, "defect"))
        qa_record = self.store.save_artifact(
            state["run_id"],
            "qa_handoff",
            release_output.qa_handoff_markdown,
            "Release Agent",
            source_artifact_ids=qa_sources,
            model_metadata=outcome.metadata(),
        )
        lineage_path = self.store.root / state["run_id"] / "lineage-runtime.json"
        lineage = JsonLineageStore(lineage_path)
        for artifact in self.store.list_artifacts(state["run_id"]):
            lineage.upsert_node(
                artifact.artifact_id,
                artifact.artifact_type,
                {"version": artifact.version, "producer_agent": artifact.producer_agent},
            )
        for artifact in self.store.list_artifacts(state["run_id"]):
            for source_id in artifact.source_artifact_ids:
                lineage.add_relationship(
                    artifact.artifact_id, "DERIVED_FROM", source_id
                )
        lineage_record = self.store.save_artifact(
            state["run_id"],
            "lineage",
            lineage.read(),
            "Release Agent",
            source_artifact_ids=[qa_record.artifact_id],
            model_metadata=outcome.metadata(),
        )
        return self._complete(
            state,
            "Release Agent",
            "Created release notes, QA handoff, and local artifact lineage.",
            {
                "release": [release_record.artifact_id],
                "qa_handoff": [qa_record.artifact_id],
                "lineage": [lineage_record.artifact_id],
            },
            attempts=outcome.attempts,
            fallback_used=outcome.fallback_used,
            updates={
                "status": "completed",
                "release_output": release_output.model_dump(mode="json"),
                "fallback_events": self._track_generation(
                    state, "Release Agent", outcome
                ),
            },
        )

    def scope_gate(self, state: WorkflowState) -> dict:
        return self._gate(state, "scope", "clarification", "scope_approved")

    def brd_gate(self, state: WorkflowState) -> dict:
        return self._gate(state, "brd", "brd", "brd_approved")

    def code_plan_gate(self, state: WorkflowState) -> dict:
        return self._gate(state, "code_plan", "code_plan", "code_plan_approved")

    def _gate(
        self,
        state: WorkflowState,
        gate: str,
        artifact_type: str,
        approval_key: str,
    ) -> dict:
        target_id = self._latest(state, artifact_type)
        decision = GateDecision.model_validate(
            interrupt(
                {
                    "type": "approval_required",
                    "gate": gate,
                    "artifact_id": target_id,
                    "message": f"Approve or reject the {gate.replace('_', ' ')} artifact.",
                }
            )
        )
        manifest = self.store.load_manifest(state["run_id"])
        approval_id = next_artifact_id(
            "approval", [item.artifact_id for item in manifest.artifacts]
        )
        approval = ApprovalRecord(
            approval_id=approval_id,
            gate=gate,
            status=ApprovalStatus(decision.status),
            artifact_id=target_id,
            actor=decision.actor,
            comment=decision.comment,
        )
        record = self.store.save_artifact(
            state["run_id"],
            "approval",
            approval,
            "HITL Gate",
            artifact_id=approval_id,
            source_artifact_ids=[target_id],
        )
        approvals = list(state.get("approvals", []))
        approvals.append(approval.model_dump(mode="json"))
        approved = decision.status == "approved"
        return {
            approval_key: approved,
            "approvals": approvals,
            "gate_feedback": {} if approved else decision.model_dump(mode="json"),
            "status": "running" if approved else "revision_required",
            "current_node": f"{gate}_gate",
            "artifact_ids": {
                **self._ids(state),
                "approval": [
                    *self._ids(state).get("approval", []),
                    record.artifact_id,
                ],
            },
        }

    def _track_generation(
        self,
        state: WorkflowState,
        agent_name: str,
        outcome: GenerationResult,
    ) -> list[dict]:
        events = list(state.get("fallback_events", []))
        if not outcome.fallback_used:
            return events
        event = {
            "agent_name": agent_name,
            "errors": list(outcome.errors),
            "fallback": "deterministic_template",
            "prompt_task": outcome.prompt_task,
            "prompt_version": outcome.prompt_version,
        }
        self.store.record_fallback_event(state["run_id"], event)
        events.append(event)
        return events

    @staticmethod
    def _latest(state: WorkflowState, artifact_type: str) -> str:
        values = state.get("artifact_ids", {}).get(artifact_type, [])
        if not values:
            raise ValueError(f"missing required artifact type: {artifact_type}")
        return values[-1]


def build_workflow(
    store: ArtifactStore,
    checkpointer: InMemorySaver | None = None,
    generator: OllamaGenerationService | None = None,
):
    nodes = WorkflowNodes(store, generator)
    graph = StateGraph(WorkflowState)
    graph.add_node("intake", nodes.intake)
    graph.add_node("context", nodes.context)
    graph.add_node("clarification", nodes.clarification)
    graph.add_node("scope_gate", nodes.scope_gate)
    graph.add_node("brd", nodes.brd)
    graph.add_node("brd_gate", nodes.brd_gate)
    graph.add_node("story", nodes.story)
    graph.add_node("plan", nodes.plan)
    graph.add_node("code_plan", nodes.code_plan)
    graph.add_node("code_plan_gate", nodes.code_plan_gate)
    graph.add_node("code_build", nodes.code_build)
    graph.add_node("git", nodes.git)
    graph.add_node("review", nodes.review)
    graph.add_node("sanity", nodes.sanity)
    graph.add_node("release", nodes.release)

    graph.add_edge(START, "intake")
    graph.add_edge("intake", "context")
    graph.add_edge("context", "clarification")
    graph.add_edge("clarification", "scope_gate")
    graph.add_conditional_edges(
        "scope_gate",
        lambda state: "approved" if state.get("scope_approved") else "rejected",
        {"approved": "brd", "rejected": "clarification"},
    )
    graph.add_edge("brd", "brd_gate")
    graph.add_conditional_edges(
        "brd_gate",
        lambda state: "approved" if state.get("brd_approved") else "rejected",
        {"approved": "story", "rejected": "brd"},
    )
    graph.add_edge("story", "plan")
    graph.add_edge("plan", "code_plan")
    graph.add_edge("code_plan", "code_plan_gate")
    graph.add_conditional_edges(
        "code_plan_gate",
        lambda state: "approved" if state.get("code_plan_approved") else "rejected",
        {"approved": "code_build", "rejected": "code_plan"},
    )
    graph.add_edge("code_build", "git")
    graph.add_edge("git", "review")
    graph.add_edge("review", "sanity")
    graph.add_edge("sanity", "release")
    graph.add_edge("release", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())
