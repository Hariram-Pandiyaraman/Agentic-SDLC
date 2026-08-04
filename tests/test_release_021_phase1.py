from pathlib import Path


SOURCE = Path("frontend/src/main.jsx").read_text(encoding="utf-8")
STYLES = Path("frontend/src/styles.css").read_text(encoding="utf-8")


def test_shell_exposes_primary_destinations_and_compact_diagnostics() -> None:
    for destination in ("Dashboard", "New run", "Approvals", "Artifacts", "Settings"):
        assert destination in SOURCE
    assert 'className="environment-popover"' in SOURCE
    assert "Open Diagnostics" in SOURCE
    assert "API unavailable" in SOURCE


def test_dashboard_has_operational_summary_filters_and_designed_states() -> None:
    for signal in ("Active runs", "Awaiting approval", "Completed", "Attention signals"):
        assert signal in SOURCE
    for control in ("Search runs", "All statuses", "Last 24 hours", "Last 7 days"):
        assert control in SOURCE
    assert "<Skeleton/>" in SOURCE
    assert "Your first run starts here" in SOURCE
    assert "No runs match these filters" in SOURCE
    assert "The API is unavailable" in SOURCE


def test_intake_is_guided_validated_and_uses_progressive_disclosure() -> None:
    for step in ("Describe", "Review", "Launch"):
        assert step in SOURCE
    assert 'aria-invalid={touched && !title.trim()}' in SOURCE
    assert "Add at least 10 characters" in SOURCE
    assert "Requirement files must be 1 MB or smaller" in SOURCE
    assert "Requirement preview" in SOURCE
    assert 'className="advanced-options"' in SOURCE
    assert "Ready to orchestrate" in SOURCE


def test_dashboard_and_intake_have_tablet_safe_layout_contracts() -> None:
    assert "@media (max-width: 900px)" in STYLES
    assert ".main { margin-left: 0" in STYLES
    assert ".run-filters { grid-template-columns: 1fr 1fr; }" in STYLES
    assert "max-width: 100%" in STYLES
    assert "overflow-x: auto" in STYLES
