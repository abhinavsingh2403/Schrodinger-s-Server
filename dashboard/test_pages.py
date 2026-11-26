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


TARGET_TEMPLATES = ["page_shell.html", "live.html"]


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
        assert ".innerHTML" not in content, f"Disallowed innerHTML assignment found in {name}"
