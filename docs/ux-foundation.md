# 0.2.1 UX foundation

This specification began as the Phase 0 UI contract. The production implementation now lives in `frontend/src`, where React components and CSS variables apply these states across the multipage experience. The Python source remains as a regression-readable record of the original token and component requirements.

## Principles

- Put the current stage and required next action before diagnostics.
- Never communicate status by color alone; pair color with a stable label and icon.
- Keep artifact identity and version visible anywhere an approval is made.
- Prefer readable structured content; raw JSON is a secondary view.
- Preserve useful page structure while secondary data loads or fails.

## Visual system

Typography uses Inter when available and Segoe UI/system sans-serif otherwise. Body text is 16 px with 1.5 line height, secondary text is 14 px, and long-form content is capped at 72 characters. Cascadia Code/Consolas is reserved for identifiers and raw data.

The spacing scale is 4, 8, 16, 24, and 32 px. Controls have a 6 px small radius; cards and panels use 12 px. A 1 px neutral border separates adjacent surfaces. Shadows are limited to raised menus and focused review panels. Icons reinforce labels and never replace them.

The responsive targets are phone (480 px), tablet (768 px), desktop (1200 px), and wide (1440 px). Desktop uses persistent navigation and may use side-by-side review. Tablet collapses secondary panels below primary content. Phone uses one column, scrollable steppers with a text summary, and a non-obscuring action area.

All normal text/background pairs in the token set are tested at or above WCAG AA 4.5:1. Focus uses a 3 px visible outline. Interactive states retain a text or shape change, and motion respects `prefers-reduced-motion`.

## State inventory

| State | Treatment | Primary information/action |
|---|---|---|
| First use | Blue information panel, plus icon, “Ready to start” | Explain the three approvals and offer New Run |
| Running | Named active step, solid dot, progress text | Current agent/stage and refresh-safe activity |
| Awaiting approval | Amber review callout, diamond icon | Gate plus exact artifact ID/version; Review |
| Rejected | Red change-request callout, revision icon | Decision comment, replacement version, resume path |
| Failed | Red assertive banner, exclamation icon | Safe cause, recovery action, Diagnostics link |
| Fallback | Orange audit callout, triangle icon | Substituted dependency/behavior and audit details |
| Complete | Green summary, check icon | Output summary, artifact review, ZIP export |

Running with fallback retains the running primary state and adds the fallback badge/banner. A rejected artifact is not labeled as a failed run. Pending workflow steps use neutral text, an outlined marker, and the word “Pending.” Blocked steps name the blocking gate.

## Reusable component boundary

Screens must compose the following contracts rather than inventing local variants: status badge, workflow stepper, metric card, empty state, approval panel, artifact card, feedback banner, and skeleton. Their required content and accessibility behavior live in `COMPONENTS` and are regression tested.

Application structure for subsequent phases is Dashboard, New Run, Run Workspace, Approvals, Artifacts, and Settings/About. Run Workspace owns Overview, Artifacts, Traceability, Activity, and Diagnostics tabs. Screen renderers may control data fetching and layout; they must consume the shared tokens and component contracts and must not redefine state colors.
