# Five-Minute Demo Narrative

1. Start FastAPI with `.\scripts\run_api.ps1`.
2. Start Streamlit with `.\scripts\run_ui.ps1`.
3. Upload `examples/sample_requirement.md`.
4. Show the normalized requirement and ranked fixture context.
5. Approve the scope gate.
6. Review the BRD and reject it once with: `State how fallback usage is audited.`
7. Open BRD versions 1 and 2, then approve the revised BRD.
8. Show the story, AC-001, sprint plan, and code plan; approve the code plan.
9. Show AC-001 in implementation metadata, code comments, tests, and review.
10. Show the sanity result, release notes, QA handoff, and lineage graph.
11. Download the complete run ZIP.

For the defect branch, start another run with **Simulate a failed sanity check**
enabled. The final QA handoff should list one open defect.

For a terminal-only fallback smoke demo, run:

```powershell
.\scripts\run_demo.ps1
```

