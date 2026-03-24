"""Tests for dashboard template rendering (Plan 05-01)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def template_client():
    from fastapi import FastAPI, Request
    from fastapi.staticfiles import StaticFiles
    from fastapi.templating import Jinja2Templates
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent.parent
    tmpl = Jinja2Templates(directory=str(base_dir / "templates"))

    app = FastAPI()

    @app.get("/")
    async def root(request: Request):
        return tmpl.TemplateResponse(request, "dashboard.html", context={})

    app.mount("/static", StaticFiles(directory=str(base_dir / "static")), name="static")

    return TestClient(app)


class TestDashboardTemplate:
    def test_root_returns_200(self, template_client):
        resp = template_client.get("/")
        assert resp.status_code == 200

    def test_root_returns_html(self, template_client):
        resp = template_client.get("/")
        assert "text/html" in resp.headers["content-type"]

    def test_root_contains_tailwind_css(self, template_client):
        resp = template_client.get("/")
        assert "tailwindcss" in resp.text

    def test_root_contains_chart_js(self, template_client):
        resp = template_client.get("/")
        assert "chart.js" in resp.text

    def test_root_contains_htmx(self, template_client):
        resp = template_client.get("/")
        assert "htmx.org" in resp.text

    def test_root_contains_gold_branding(self, template_client):
        resp = template_client.get("/")
        assert "Gold Advisor" in resp.text

    def test_root_has_vietnamese_lang(self, template_client):
        resp = template_client.get("/")
        assert 'lang="vi"' in resp.text

    def test_root_has_viewport_meta(self, template_client):
        resp = template_client.get("/")
        assert "viewport" in resp.text


class TestStaticFiles:
    def test_css_main_returns_200(self, template_client):
        resp = template_client.get("/static/css/main.css")
        assert resp.status_code == 200

    def test_css_contains_gold_variables(self, template_client):
        resp = template_client.get("/static/css/main.css")
        assert "--gold:" in resp.text or "gold" in resp.text.lower()
