import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import patch, MagicMock
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


@pytest.fixture
def template_env():
    base_dir = Path(__file__).resolve().parent.parent
    templates_dir = base_dir / "templates"
    return Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)


@pytest.fixture
def partial_app():
    from src.api.routes.dashboard import router

    app = FastAPI()
    app.include_router(router, prefix="/dashboard", tags=["dashboard"])
    client = TestClient(app)
    yield client


class TestMacroPartial:
    def test_partial_returns_200(self, partial_app):
        resp = partial_app.get("/dashboard/partials/macro")
        assert resp.status_code == 200

    def test_partial_contains_macro_label(self, partial_app):
        resp = partial_app.get("/dashboard/partials/macro")
        assert "Macro" in resp.text or "USD/VND" in resp.text or "DXY" in resp.text

    def test_partial_renders_as_html(self, partial_app):
        resp = partial_app.get("/dashboard/partials/macro")
        assert "<" in resp.text
        assert ">" in resp.text


class TestMacroPartialTemplate:
    def test_template_renders_with_fx_data(self, template_env):
        template = template_env.get_template("partials/macro_card.html")
        html = template.render(
            fx_trend={
                "current_rate": 25500.0,
                "trend": "up",
                "change_pct": 2.5,
                "ma_7d": 25400.0,
                "ma_30d": 25000.0,
            },
            gold_trend={
                "current_price": 2700.0,
                "trend": "up",
                "momentum": 3.0,
                "ma_7d": 2680.0,
                "ma_30d": 2620.0,
            },
            dxy=104.5,
        )
        assert "25,500" in html
        assert "2,700" in html
        assert "104.5" in html

    def test_template_renders_empty_state(self, template_env):
        template = template_env.get_template("partials/macro_card.html")
        html = template.render(
            fx_trend=None,
            gold_trend=None,
            dxy=None,
        )
        assert "No macro data" in html

    def test_template_shows_up_arrow_for_rising_fx(self, template_env):
        template = template_env.get_template("partials/macro_card.html")
        html = template.render(
            fx_trend={
                "current_rate": 25500.0,
                "trend": "up",
                "change_pct": 2.5,
                "ma_7d": 25400.0,
                "ma_30d": 25000.0,
            },
            gold_trend=None,
            dxy=None,
        )
        assert "↑" in html or "up" in html.lower() or "arrow" in html.lower()

    def test_template_shows_down_arrow_for_falling_gold(self, template_env):
        template = template_env.get_template("partials/macro_card.html")
        html = template.render(
            fx_trend=None,
            gold_trend={
                "current_price": 2600.0,
                "trend": "down",
                "momentum": -2.0,
                "ma_7d": 2620.0,
                "ma_30d": 2650.0,
            },
            dxy=None,
        )
        assert "red-400" in html
