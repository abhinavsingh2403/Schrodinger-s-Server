"""Contract tests for dashboard page shells, navigation, anti-hallucination and security."""
from io import BytesIO
import json
from pathlib import Path
import pytest
from dashboard.app import DashboardServer, PAGE_TITLES, make_dashboard_handler

ROUTES = ["/", *PAGE_TITLES.keys()]

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
]

# Sensitive fixture numerical values that must NEVER be hardcoded into templates
FIXTURE_NUMBERS = [
    "0.063583",
    "0.35634",
    "0.049105",
    "100793",
    "325456",
    "157.6092",
    "402.3183",
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


TARGET_TEMPLATES = ["page_shell.html", "live.html", "index.html"]

EXTERNAL_URL_PATTERNS = [
    "cdn.tailwindcss.com",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "unpkg.com",
    "cdnjs.cloudflare.com",
]


@pytest.mark.parametrize("route", ROUTES)
def test_page_routes_return_200_with_nav_and_banner(route: str):
    code, html = render_route(route)
    assert code == 200
    assert 'id="banner"' in html
    assert "<nav" in html
    assert 'href="/"' in html
    assert 'href="/evidence"' in html
    assert 'href="/ml"' in html
    assert 'href="/cost"' in html
    assert 'href="/session"' in html
    assert 'href="/visitors"' in html
    assert 'href="/deception"' in html
    assert 'href="/lab"' in html


def test_research_archive_route_returns_200():
    code, html = render_route("/research")
    assert code == 200
    assert "<nav" in html
    assert "<footer" in html


def test_no_fixture_data_literals_in_templates():
    template_dir = Path(__file__).resolve().parent / "templates"
    for name in TARGET_TEMPLATES:
        content = (template_dir / name).read_text(encoding="utf-8")
        for num in FIXTURE_NUMBERS:
            assert num not in content, f"Hardcoded fixture literal {num} found in {name}"


def test_no_forbidden_phrases_in_templates():
    template_dir = Path(__file__).resolve().parent / "templates"
    for name in TARGET_TEMPLATES:
        content = (template_dir / name).read_text(encoding="utf-8")
        for phrase in FORBIDDEN_PHRASES:
            assert phrase.lower() not in content.lower(), f"Forbidden phrase '{phrase}' in {name}"


def test_no_inner_html_with_data_in_templates():
    template_dir = Path(__file__).resolve().parent / "templates"
    for name in TARGET_TEMPLATES:
        content = (template_dir / name).read_text(encoding="utf-8")
        for disallowed in [".innerHTML", ".outerHTML", "insertAdjacentHTML", "document.write"]:
            assert disallowed not in content, f"Disallowed DOM method '{disallowed}' found in {name}"


def test_no_external_cdn_or_font_imports():
    template_dir = Path(__file__).resolve().parent / "templates"
    for name in TARGET_TEMPLATES:
        content = (template_dir / name).read_text(encoding="utf-8")
        for url_pattern in EXTERNAL_URL_PATTERNS:
            assert url_pattern not in content, f"External resource import '{url_pattern}' found in {name}"


@pytest.mark.parametrize("route", ROUTES)
def test_page_routes_have_footer(route: str):
    code, html = render_route(route)
    assert code == 200
    assert "<footer" in html


def test_prefers_reduced_motion_present():
    template_dir = Path(__file__).resolve().parent / "templates"
    for name in TARGET_TEMPLATES:
        content = (template_dir / name).read_text(encoding="utf-8")
        assert "prefers-reduced-motion" in content, f"prefers-reduced-motion missing from {name}"


def test_interactive_elements_have_accessible_labels():
    template_dir = Path(__file__).resolve().parent / "templates"
    for name in TARGET_TEMPLATES:
        content = (template_dir / name).read_text(encoding="utf-8")
        assert "aria-label" in content, f"aria-label accessibility attributes missing from {name}"


PRIMARY_LABELS = {
    "/": "Mission Control", "/session": "Session Forensics", "/visitors": "Visitor Atlas",
    "/deception": "Deception Engine", "/ml": "Model & Research",
}
FOOTER_ROUTES = ["/evidence", "/cost", "/replay", "/detector", "/lab", "/research"]


@pytest.mark.parametrize("route", [*PRIMARY_LABELS, *FOOTER_ROUTES, "/index.html"])
def test_preserved_routes_and_navigation(route):
    from html import unescape
    import re

    status, html = render_route(route)
    assert status == 200
    nav = re.search(r'<nav class="topnav"[^>]*>(.*?)</nav>', html, re.S)[1]
    links = re.findall(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', unescape(nav))
    assert links == list(PRIMARY_LABELS.items())
    footer = re.search(r'<footer[^>]*>.*?<nav aria-label="Evidence &amp; Proof">(.*?)</nav>', html, re.S)[1]
    assert re.findall(r'href="([^"]+)"', footer) == FOOTER_ROUTES
    current = "/" if route == "/index.html" else route
    assert re.findall(r'href="([^"]+)" class="active" aria-current="page"', nav + footer) == [current]
    title = re.search(r'<title>(.*?)</title>', html)[1]
    assert PRIMARY_LABELS.get(current, PAGE_TITLES.get(current, "Research Archive")) in unescape(title)
