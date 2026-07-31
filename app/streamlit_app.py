"""Streamlit operating console for the SDLC Agentic Framework."""

import json
import sys
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sdlc.config import get_settings

settings = get_settings()
API = settings.api_base_url.rstrip("/")
AGENT_ORDER = [
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
]
ARTIFACT_GROUPS = {
    "Requirements": {"requirement", "context_pack", "clarification"},
    "BRD": {"brd", "approval"},
    "Backlog": {"backlog"},
    "Planning": {"sprint_plan", "code_plan"},
    "Code": {"code", "test_case", "git_plan"},
    "Validation": {"review", "test_result", "defect"},
    "Release": {"release", "qa_handoff", "lineage"},
}


def api_request(
    method: str,
    path: str,
    *,
    payload: dict | None = None,
    timeout: float = 30.0,
) -> httpx.Response:
    response = httpx.request(
        method,
        f"{API}{path}",
        json=payload,
        timeout=timeout,
    )
    response.raise_for_status()
    return response


def load_run(run_id: str) -> dict | None:
    try:
        return api_request("GET", f"/api/v1/runs/{run_id}").json()
    except httpx.HTTPError as exc:
        st.error(f"Unable to load run {run_id}: {exc}")
        return None


def render_health() -> None:
    with st.sidebar:
        st.header("Environment")
        st.code(f"API: {API}\nOllama enabled: {settings.use_ollama}")
        if st.button("Check services", use_container_width=True):
            try:
                health = api_request("GET", "/health", timeout=5).json()
                if health["status"] == "ready":
                    st.success("All configured services are ready.")
                else:
                    st.warning("External services unavailable; fallbacks are active.")
                st.json(health)
            except httpx.HTTPError as exc:
                st.error(f"FastAPI is not reachable: {exc}")


def render_submission() -> None:
    st.subheader("Start a feature run")
    uploaded = st.file_uploader(
        "Optional requirement file",
        type=["txt", "md"],
        help="Uploaded text replaces the requirement entered below.",
    )
    with st.form("new-run"):
        title = st.text_input("Feature title", value="Traceable feature delivery")
        requirement = st.text_area(
            "Requirement",
            height=180,
            placeholder="Describe the feature, users, rules, constraints, and desired outcome.",
        )
        simulate_failure = st.checkbox(
            "Simulate a failed sanity check",
            help="Useful for demonstrating structured defect creation.",
        )
        submitted = st.form_submit_button("Start workflow", type="primary")
    if not submitted:
        return
    if uploaded is not None:
        requirement = uploaded.getvalue().decode("utf-8", errors="replace")
    if len(requirement.strip()) < 10:
        st.error("Enter a requirement containing at least 10 characters.")
        return
    try:
        response = api_request(
            "POST",
            "/api/v1/runs",
            payload={
                "title": title,
                "raw_requirement": requirement,
                "simulate_test_failure": simulate_failure,
            },
            timeout=90,
        ).json()
        st.session_state.run_id = response["run_id"]
        st.success(f"Started {response['run_id']}")
        st.rerun()
    except httpx.HTTPError as exc:
        st.error(f"Unable to start workflow: {exc}")


def render_progress(run: dict) -> None:
    state = run.get("state", {})
    results = state.get("agent_results", [])
    completed = {result["agent_name"] for result in results}
    st.subheader("Workflow progress")
    st.progress(len(completed) / len(AGENT_ORDER))
    columns = st.columns(3)
    for index, agent in enumerate(AGENT_ORDER):
        marker = "Complete" if agent in completed else "Pending"
        columns[index % 3].write(f"{marker}: {agent}")
    st.caption(
        f"Status: {run.get('status', 'unknown')} | "
        f"Current: {state.get('current_node', 'unknown')} | "
        f"Fallback events: {len(state.get('fallback_events', []))}"
    )


def render_approval(run: dict) -> None:
    interrupts = run.get("interrupts", [])
    if not interrupts:
        return
    request = interrupts[0]["value"]
    st.warning(
        f"Approval required: {request['gate'].replace('_', ' ').title()} "
        f"({request['artifact_id']})"
    )
    try:
        artifact = api_request(
            "GET",
            f"/api/v1/runs/{run['run_id']}/artifacts/{request['artifact_id']}",
        ).text
        with st.expander("Review approval artifact", expanded=True):
            st.markdown(artifact)
    except httpx.HTTPError as exc:
        st.error(f"Unable to load approval artifact: {exc}")

    with st.form(f"approval-{request['gate']}-{request['artifact_id']}"):
        actor = st.text_input("Approver", value="Solution Architect")
        comment = st.text_area("Decision comment")
        approve_col, reject_col = st.columns(2)
        approved = approve_col.form_submit_button("Approve", type="primary")
        rejected = reject_col.form_submit_button("Reject")
    if not approved and not rejected:
        return
    if rejected and not comment.strip():
        st.error("A rejection requires a comment.")
        return
    try:
        api_request(
            "POST",
            f"/api/v1/runs/{run['run_id']}/resume",
            payload={
                "status": "approved" if approved else "rejected",
                "actor": actor,
                "comment": comment or ("Approved" if approved else None),
            },
            timeout=90,
        )
        st.rerun()
    except httpx.HTTPError as exc:
        st.error(f"Unable to submit decision: {exc}")


def render_artifact(record: dict, run_id: str) -> None:
    label = (
        f"{record['artifact_id']} v{record['version']} — "
        f"{record['producer_agent']}"
    )
    with st.expander(label):
        try:
            response = api_request(
                "GET",
                f"/api/v1/runs/{run_id}/artifacts/{record['artifact_id']}"
                f"?version={record['version']}",
            )
            content = response.text
            if record["media_type"] == "application/json":
                st.json(json.loads(content))
            else:
                st.markdown(content)
            st.download_button(
                "Download artifact",
                data=response.content,
                file_name=record["relative_path"],
                mime=record["media_type"],
                key=f"download-{record['artifact_id']}-{record['version']}",
            )
            metadata = record.get("model_metadata", {})
            if metadata:
                st.caption(
                    f"Provider: {metadata.get('provider')} | "
                    f"Prompt: {metadata.get('prompt_task')} "
                    f"v{metadata.get('prompt_version')} | "
                    f"Fallback: {metadata.get('fallback_used')}"
                )
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            st.error(f"Unable to display artifact: {exc}")


def render_lineage(run_id: str) -> None:
    try:
        graph = api_request("GET", f"/api/v1/runs/{run_id}/lineage").json()
    except httpx.HTTPError:
        st.info("Lineage visualization becomes available after release generation.")
        return
    lines = ["digraph lineage {", "rankdir=LR;", "node [shape=box];"]
    for node_id, node in graph.get("nodes", {}).items():
        label = f"{node_id}\\n{node.get('artifact_type', '')}".replace('"', "'")
        lines.append(f'"{node_id}" [label="{label}"];')
    for edge in graph.get("relationships", []):
        lines.append(
            f'"{edge["source_id"]}" -> "{edge["target_id"]}" '
            f'[label="{edge["relationship"]}"];'
        )
    lines.append("}")
    st.graphviz_chart("\n".join(lines), use_container_width=True)


def render_results(run: dict) -> None:
    artifacts = run.get("artifacts", [])
    if not artifacts:
        return
    st.subheader("Run artifacts")
    tabs = st.tabs([*ARTIFACT_GROUPS, "Lineage"])
    for tab, (group_name, types) in zip(tabs, ARTIFACT_GROUPS.items()):
        with tab:
            records = [item for item in artifacts if item["artifact_type"] in types]
            if not records:
                st.info(f"No {group_name.lower()} artifacts yet.")
            for record in records:
                render_artifact(record, run["run_id"])
    with tabs[-1]:
        render_lineage(run["run_id"])

    try:
        export = api_request("GET", f"/api/v1/runs/{run['run_id']}/export")
        st.download_button(
            "Download complete run",
            data=export.content,
            file_name=f"{run['run_id']}.zip",
            mime="application/zip",
            type="primary",
        )
    except httpx.HTTPError as exc:
        st.error(f"Unable to prepare run export: {exc}")


st.set_page_config(page_title="SDLC Agentic Framework", layout="wide")
st.title("SDLC Agentic Framework")
st.caption("Requirement-to-QA automation with architect approval gates")
render_health()

if "run_id" not in st.session_state:
    st.session_state.run_id = None

render_submission()

if st.session_state.run_id:
    toolbar_left, toolbar_right = st.columns([4, 1])
    toolbar_left.info(f"Active run: {st.session_state.run_id}")
    if toolbar_right.button("Refresh", use_container_width=True):
        st.rerun()
    current_run = load_run(st.session_state.run_id)
    if current_run:
        render_progress(current_run)
        render_approval(current_run)
        render_results(current_run)
