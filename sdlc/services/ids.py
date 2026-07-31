"""Stable, readable identifiers for runs and artifacts."""

import re
from datetime import UTC, datetime
from uuid import uuid4

ARTIFACT_PREFIXES = {
    "requirement": "REQ",
    "context_pack": "CTX",
    "clarification": "CLAR",
    "brd": "BRD",
    "backlog": "BACKLOG",
    "epic": "EPIC",
    "story": "US",
    "acceptance_criterion": "AC",
    "sprint_plan": "PLAN",
    "code_plan": "CODEPLAN",
    "code": "CODE",
    "git_plan": "GIT",
    "review": "REV",
    "test_case": "TC",
    "test_result": "TR",
    "defect": "DEF",
    "release": "REL",
    "qa_handoff": "QA",
    "lineage": "LIN",
    "approval": "APR",
}

SAFE_ID = re.compile(r"^[A-Z][A-Z0-9_-]*$")


def new_run_id(now: datetime | None = None) -> str:
    timestamp = (now or datetime.now(UTC)).strftime("%Y%m%dT%H%M%SZ")
    return f"RUN-{timestamp}-{uuid4().hex[:8].upper()}"


def artifact_prefix(artifact_type: str) -> str:
    normalized = artifact_type.strip().lower()
    if normalized not in ARTIFACT_PREFIXES:
        raise ValueError(f"unsupported artifact type: {artifact_type}")
    return ARTIFACT_PREFIXES[normalized]


def next_artifact_id(artifact_type: str, existing_ids: list[str]) -> str:
    prefix = artifact_prefix(artifact_type)
    pattern = re.compile(rf"^{re.escape(prefix)}-(\d+)$")
    numbers = [
        int(match.group(1))
        for artifact_id in existing_ids
        if (match := pattern.match(artifact_id))
    ]
    return f"{prefix}-{max(numbers, default=0) + 1:03d}"


def validate_safe_id(value: str, label: str = "ID") -> str:
    if not SAFE_ID.fullmatch(value):
        raise ValueError(f"{label} must contain only uppercase letters, digits, '-' or '_'")
    return value
