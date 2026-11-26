"""Exercise each GET handler without opening a network socket."""
from io import BytesIO
import pytest
from dashboard.app import DashboardServer, PAGE_TITLES, make_dashboard_handler

@pytest.mark.parametrize("path", PAGE_TITLES)
def test_shell(path):
    cls = make_dashboard_handler(DashboardServer())
    request = object.__new__(cls)
    request.path = path
    request.wfile = BytesIO()
    codes = []
    request.send_response = codes.append
    request.send_header = lambda *_: None
    request.end_headers = lambda: None
    request.do_GET()
    html = request.wfile.getvalue().decode()
    assert codes == [200]
    assert PAGE_TITLES[path] in html and "Scope UNKNOWN" in html
    assert "Policy profile UNKNOWN" in html and "NO DATA" in html
