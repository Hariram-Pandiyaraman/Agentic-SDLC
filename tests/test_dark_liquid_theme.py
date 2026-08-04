from pathlib import Path


STYLES = Path("frontend/src/styles.css").read_text(encoding="utf-8")
INDEX = Path("frontend/index.html").read_text(encoding="utf-8")


def test_dark_liquid_glass_theme_covers_the_application_shell() -> None:
    assert "color-scheme: dark" in STYLES
    assert "--glass: linear-gradient" in STYLES
    assert "backdrop-filter: blur(34px) saturate(180%)" in STYLES
    assert ".app-shell::before, .app-shell::after" in STYLES
    assert "@keyframes liquid-drift" in STYLES
    assert '<meta name="theme-color" content="#050711"' in INDEX


def test_dark_treatments_cover_interactive_and_overlay_surfaces() -> None:
    for selector in (
        ".sidebar", ".hero", ".metric-card", ".form-card", ".panel",
        ".modal, .drawer", ".artifact-card", ".lineage-node", ".health-service",
        ".mobile-bar",
    ):
        assert selector in STYLES
    assert "input::placeholder, textarea::placeholder" in STYLES
    assert ":focus-visible" in STYLES
    assert "@media (prefers-reduced-motion: reduce)" in STYLES
