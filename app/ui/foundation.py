"""Executable design tokens and component contracts for the 0.2.1 UI."""

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType


COLORS = MappingProxyType({
    "canvas": "#F4F7FB", "surface": "#FFFFFF", "surface_subtle": "#EAF0F7",
    "text": "#172033", "text_muted": "#526077", "border": "#C7D1DE",
    "primary": "#0B5CAD", "primary_hover": "#084780", "focus": "#005FCC",
    "success": "#176B3A", "success_surface": "#E8F5ED",
    "warning": "#6A4500", "warning_surface": "#FFF2CC",
    "danger": "#9D2521", "danger_surface": "#FCEAE8",
    "info": "#075985", "info_surface": "#E6F2FA",
    "fallback": "#7A4300", "fallback_surface": "#FFF0D6",
    "disabled": "#667085", "disabled_surface": "#EAECF0",
})

TYPOGRAPHY = MappingProxyType({
    "family": "Inter, Segoe UI, system-ui, -apple-system, sans-serif",
    "mono_family": "Cascadia Code, Consolas, monospace",
    "body_size": "1rem", "small_size": "0.875rem", "h1_size": "2rem",
    "h2_size": "1.5rem", "line_height": "1.5", "content_width": "72ch",
})
SPACING = MappingProxyType(
    {"xs": "0.25rem", "sm": "0.5rem", "md": "1rem", "lg": "1.5rem", "xl": "2rem"}
)
BREAKPOINTS = MappingProxyType(
    {"phone": 480, "tablet": 768, "desktop": 1200, "wide": 1440}
)


class WorkflowVisualState(StrEnum):
    """Canonical states whose labels and icons prevent color-only meaning."""

    FIRST_USE = "first_use"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    REJECTED = "rejected"
    FAILED = "failed"
    FALLBACK = "fallback"
    COMPLETE = "complete"


@dataclass(frozen=True)
class StateTreatment:
    label: str
    icon: str
    foreground: str
    background: str
    guidance: str
    aria_live: str = "polite"


STATE_TREATMENTS = MappingProxyType({
    WorkflowVisualState.FIRST_USE: StateTreatment(
        "Ready to start", "+", COLORS["info"], COLORS["info_surface"],
        "Explain the workflow and show one clear New Run action."),
    WorkflowVisualState.RUNNING: StateTreatment(
        "In progress", "*", COLORS["primary"], COLORS["surface"],
        "Name the active stage, show known progress, and keep refresh non-blocking."),
    WorkflowVisualState.AWAITING_APPROVAL: StateTreatment(
        "Approval required", "◆", COLORS["warning"], COLORS["warning_surface"],
        "Identify the gate and exact artifact version; make review the primary action."),
    WorkflowVisualState.REJECTED: StateTreatment(
        "Changes requested", "↺", COLORS["danger"], COLORS["danger_surface"],
        "Show the decision comment and revised version without implying workflow failure."),
    WorkflowVisualState.FAILED: StateTreatment(
        "Action needed", "!", COLORS["danger"], COLORS["danger_surface"],
        "Give a safe error summary, recovery action, and diagnostics link.", "assertive"),
    WorkflowVisualState.FALLBACK: StateTreatment(
        "Fallback active", "△", COLORS["fallback"], COLORS["fallback_surface"],
        "Name the substituted service or behavior and preserve the audit detail."),
    WorkflowVisualState.COMPLETE: StateTreatment(
        "Complete", "✓", COLORS["success"], COLORS["success_surface"],
        "Summarize outputs and offer artifact review or complete-run export."),
})


@dataclass(frozen=True)
class ComponentSpec:
    purpose: str
    required_content: tuple[str, ...]
    accessibility: tuple[str, ...]


COMPONENTS = MappingProxyType({
    "status_badge": ComponentSpec("Communicate workflow or service state.",
        ("icon", "visible label"), ("never color-only", "programmatic status text")),
    "workflow_stepper": ComponentSpec("Show every workflow stage and state.",
        ("ordered stage name", "state", "current-stage marker"),
        ("ordered-list semantics", "text equivalent", "keyboard-safe overflow")),
    "metric_card": ComponentSpec("Summarize a count or operational signal.",
        ("label", "value", "optional trend or action"),
        ("logical heading order", "no color-only trend")),
    "empty_state": ComponentSpec("Explain why content is absent and how to proceed.",
        ("plain-language title", "guidance", "optional primary action"),
        ("action has an explicit label",)),
    "approval_panel": ComponentSpec("Support a version-safe human decision.",
        ("gate", "artifact ID and version", "preview", "history", "comment", "actions"),
        ("persistent labels", "rejection comment required", "target repeated near actions")),
    "artifact_card": ComponentSpec("Preview and open a generated artifact.",
        ("type", "artifact ID", "version", "producer", "approval state", "actions"),
        ("descriptive action labels", "metadata available as text")),
    "feedback_banner": ComponentSpec("Report success, warning, fallback, or error feedback.",
        ("icon", "title", "message", "optional recovery action"),
        ("appropriate live region", "dismiss control has a label")),
    "skeleton": ComponentSpec("Reserve layout while data loads.",
        ("shape matching expected content", "loading label"),
        ("reduced-motion safe", "not exposed as finished content")),
})


def foundation_css() -> str:
    """Return shared CSS variables and accessibility defaults for later screens."""

    color_vars = "\n".join(
        f"  --color-{name.replace('_', '-')}: {value};" for name, value in COLORS.items()
    )
    spacing_vars = "\n".join(f"  --space-{name}: {value};" for name, value in SPACING.items())
    return f""":root {{
{color_vars}
{spacing_vars}
  --font-sans: {TYPOGRAPHY['family']};
  --font-mono: {TYPOGRAPHY['mono_family']};
  --radius-sm: 0.375rem;
  --radius-md: 0.75rem;
  --shadow-sm: 0 1px 2px rgba(23, 32, 51, 0.08);
  --shadow-md: 0 8px 24px rgba(23, 32, 51, 0.12);
}}
:focus-visible {{ outline: 3px solid var(--color-focus); outline-offset: 2px; }}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ scroll-behavior: auto !important; transition: none !important; }}
}}"""
