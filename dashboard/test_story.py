"""Comprehensive tests for the 5-page dashboard visual storytelling, contract and claims."""
import re
from io import BytesIO
from pathlib import Path
import pytest
from dashboard.app import DashboardServer, make_dashboard_handler, PRIMARY, SECONDARY

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = ROOT / "dashboard" / "templates"
TARGET_TEMPLATES = ["live.html", "page_shell.html", "index.html"]

PRIMARY_ROUTES = ["/", "/session", "/visitors", "/deception", "/ml"]
FOOTER_ROUTES = ["/evidence", "/cost", "/replay", "/detector", "/lab", "/research"]

FORBIDDEN_PHRASES = [
    "ML works",
    "cost savings",
    "saves money",
    "reduces load",
    "blocks attacks",
    "filters attacks",
    "real attackers",
    "safety PASS",
    "₹",
    "rupee",
    "better than",
]

EXTERNAL_URL_PATTERNS = [
    "cdn.tailwindcss.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "unpkg.com",
    "cdnjs.cloudflare.com",
]


def render_route(path: str) -> tuple[int, str]:
    cls = make_dashboard_handler(DashboardServer())
    req = object.__new__(cls)
    req.path = path
    req.wfile = BytesIO()
    status_codes = []
    req.send_response = status_codes.append
    req.send_header = lambda *_: None
    req.end_headers = lambda: None
    req.do_GET()
    return status_codes[0], req.wfile.getvalue().decode("utf-8")


@pytest.mark.parametrize("route", PRIMARY_ROUTES)
def test_primary_routes_render_200_with_five_nav_items(route: str):
    code, html = render_route(route)
    assert code == 200
    assert 'id="banner"' in html
    assert "<nav" in html
    assert "<footer" in html

    # Exactly 5 items in primary navigation
    nav_match = re.search(r'<nav class="topnav"[^>]*>(.*?)</nav>', html, re.S)
    assert nav_match is not None, f"Top navigation missing in {route}"
    nav_html = nav_match.group(1)
    links = re.findall(r'<a href="([^"]+)"', nav_html)
    assert len(links) == 5, f"Expected exactly 5 primary nav links, found {len(links)}: {links}"
    assert links == list(PRIMARY)


@pytest.mark.parametrize("route", PRIMARY_ROUTES)
def test_footer_evidence_and_proof_navigation(route: str):
    code, html = render_route(route)
    assert code == 200
    footer_match = re.search(r'<footer[^>]*>.*?<nav aria-label="Evidence &amp; Proof">(.*?)</nav>', html, re.S)
    assert footer_match is not None, f"Evidence & Proof footer missing in {route}"
    footer_links = re.findall(r'href="([^"]+)"', footer_match.group(1))
    assert footer_links == list(SECONDARY)


def test_no_forbidden_phrases_or_external_urls():
    for name in TARGET_TEMPLATES:
        content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
        for phrase in FORBIDDEN_PHRASES:
            assert phrase.lower() not in content.lower(), f"Forbidden phrase '{phrase}' in {name}"
        for url in EXTERNAL_URL_PATTERNS:
            assert url not in content, f"External url '{url}' in {name}"


def test_no_inner_html_or_dom_injection():
    for name in TARGET_TEMPLATES:
        content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
        for disallowed in [".innerHTML", ".outerHTML", "insertAdjacentHTML", "document.write"]:
            assert disallowed not in content, f"Disallowed DOM method '{disallowed}' in {name}"


def test_no_code_slop_or_todo():
    for name in TARGET_TEMPLATES:
        content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
        for slop in ["TODO", "FIXME", "console.log", "lorem ipsum"]:
            assert slop.lower() not in content.lower(), f"Code slop token '{slop}' in {name}"


def test_accessibility_aria_labels_and_text_alternatives():
    for name in ["live.html", "page_shell.html"]:
        content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
        assert "aria-label" in content
        assert "role=" in content
        # Check text alternatives for visualizations
        if name == "live.html":
            assert "galaxy-alt-list" in content
            assert "Illustration" in content
            assert "Replay of recorded decisions" in content


def test_motion_and_print_modes():
    for name in ["live.html", "page_shell.html"]:
        content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
        assert "prefers-reduced-motion" in content
        assert "@media print" in content
        assert "presentation-mode" in content
        assert "initPresentationMode" in content


def test_keyboard_controls_implemented():
    for name in ["live.html", "page_shell.html"]:
        content = (TEMPLATES_DIR / name).read_text(encoding="utf-8")
        assert "keydown" in content
        assert "ArrowRight" in content
        assert "ArrowLeft" in content
        assert "Escape" in content


def test_named_constants_and_caps():
    live_content = (TEMPLATES_DIR / "live.html").read_text(encoding="utf-8")
    assert "const MAX_GALAXY_PARTICLES = 50;" in live_content
    assert "const TIME_BUCKET_MINUTES = 60;" in live_content
    assert "const TOUR_STEPS = 5;" in live_content
    assert "const MAX_RECENT_SESSIONS = 50;" in live_content

    shell_content = (TEMPLATES_DIR / "page_shell.html").read_text(encoding="utf-8")
    assert "const MAX_GRAPH_NODES = 30;" in shell_content


def test_story_sentences_exist_in_templates():
    story_file = ROOT / "docs" / "FRONTEND_STORY.md"
    assert story_file.exists(), "docs/FRONTEND_STORY.md must exist"
    story_text = story_file.read_text(encoding="utf-8")

    all_templates = "\n".join((TEMPLATES_DIR / name).read_text(encoding="utf-8") for name in TARGET_TEMPLATES)

    # Core conceptual takeaway sentences
    takeaways = [
        "A cheap gatekeeper decides from initial events which sessions receive higher-fidelity deception.",
        "Individual session progression reveals the exact moment and mechanism of tier escalation.",
        "Visitor memory tracks past interactions across sessions while Docker bridge limitations merge lab identities.",
        "In-process session adaptation switches personas dynamically between T1 Lite and T2 Hardened.",
        "Rigorous empirical evaluation against null controls showed no validated ML gain over simple baselines.",
    ]
    for s in takeaways:
        assert s in all_templates, f"Takeaway sentence missing from templates: {s}"


def test_all_new_css_classes_referenced():
    live_content = (TEMPLATES_DIR / "live.html").read_text(encoding="utf-8")
    new_live_classes = [
        "tour-box", "tour-header", "tour-stepper", "tour-step-btn", "tour-caption",
        "tour-actions", "pipeline-card", "pipeline-svg", "galaxy-card", "galaxy-canvas",
        "galaxy-legend", "galaxy-alt-list", "latency-strip", "checklist-grid", "check-item",
        "sparkline-box", "sparkline-svg", "funnel-container", "funnel-row", "funnel-label",
        "funnel-bar-track", "funnel-bar-t1", "funnel-bar-t2", "takeaway-banner", "presentation-mode",
    ]
    for c in new_live_classes:
        assert c in live_content, f"New CSS class '{c}' not referenced in live.html"

    shell_content = (TEMPLATES_DIR / "page_shell.html").read_text(encoding="utf-8")
    new_shell_classes = [
        "scrubber-card", "scrubber-track-horiz", "scrubber-track-line", "scrubber-stage-node",
        "scrubber-node-dot", "escalation-moment-badge", "highlight-300ms", "takeaway-banner",
        "presentation-mode", "context-inspector-panel", "chart-bar",
    ]
    for c in new_shell_classes:
        assert c in shell_content, f"New CSS class '{c}' not referenced in page_shell.html"

