import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.config import Settings, VNTZ
from src.engine.pipeline import compute_signal
from src.engine.types import SignalMode
from src.storage.database import async_session
from src.storage.repository import get_latest_prices, get_recent_news

from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _vn_time(value, fmt="%d/%m/%Y %H:%M"):
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value[:19] if len(value) >= 19 else value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(VNTZ).strftime(fmt)


templates.env.filters["vn_time"] = _vn_time


def get_settings() -> Settings:
    return Settings()


def _get_db_path() -> str:
    settings = get_settings()
    url = settings.database_url
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            return url[len(prefix) :]
    return url


@router.get("/prices")
async def get_dashboard_prices():
    async with async_session() as session:
        prices = await get_latest_prices(session)

    if not prices:
        return {"dealers": []}

    grouped: dict[str, dict] = defaultdict(
        lambda: {"source": "", "products": [], "fetched_at": None}
    )

    for p in prices:
        entry = grouped[p.source]
        entry["source"] = p.source

        if p.product_type == "xau_usd":
            product = {
                "product_type": p.product_type,
                "price_usd": p.price_usd,
                "price_vnd": p.price_vnd,
            }
        else:
            product = {
                "product_type": p.product_type,
                "buy_price": p.buy_price,
                "sell_price": p.sell_price,
                "spread": p.spread,
            }

        entry["products"].append(product)
        if p.fetched_at:
            current = entry.get("_max_fetched_at")
            if current is None or p.fetched_at > current:
                entry["_max_fetched_at"] = p.fetched_at

    for entry in grouped.values():
        raw = entry.pop("_max_fetched_at", None)
        if raw:
            vn_dt = (
                raw.astimezone(VNTZ)
                if raw.tzinfo
                else raw.replace(tzinfo=timezone.utc).astimezone(VNTZ)
            )
            entry["fetched_at"] = vn_dt.isoformat()

    return {"dealers": list(grouped.values())}


@router.get("/signal")
async def get_dashboard_signal(
    mode: str = Query("saver", pattern="^(saver|trader)$"),
):
    from datetime import datetime, timezone

    signal_mode = SignalMode(mode.upper())
    signal = await asyncio.to_thread(compute_signal, _get_db_path(), signal_mode)

    if signal.confidence == 0 and signal.recommendation == "HOLD":
        return JSONResponse(
            status_code=503,
            content={"error": "insufficient data"},
        )

    month = datetime.now(timezone.utc).month
    from src.engine.seasonal import get_seasonal_demand_level, compute_seasonal_modifier

    seasonal_info = {
        "month": month,
        "demand_level": get_seasonal_demand_level(month),
        "modifier": compute_seasonal_modifier(month),
    }

    policy_info = None
    try:
        from src.engine.policy import compute_policy_signal

        policy_info = await asyncio.to_thread(compute_policy_signal, _get_db_path())
    except Exception:
        pass

    result = signal.__dict__
    result["seasonal_demand_level"] = seasonal_info["demand_level"]
    result["active_policy_events"] = (
        len(policy_info["active_events"]) if policy_info else 0
    )
    return result


@router.get("/partials/signal")
async def get_signal_partial(
    request: Request,
    mode: str = Query("saver", pattern="^(saver|trader)$"),
):
    try:
        from datetime import datetime, timezone

        signal_mode = SignalMode(mode.upper())
        signal = await asyncio.to_thread(compute_signal, _get_db_path(), signal_mode)

        gap = None
        if signal.gap_vnd is not None:
            from src.analysis.gap import calculate_current_gap

            gap_result = await asyncio.to_thread(calculate_current_gap, _get_db_path())
            gap = gap_result

        month = datetime.now(timezone.utc).month
        from src.engine.seasonal import (
            get_seasonal_demand_level,
            compute_seasonal_modifier,
        )

        seasonal_info = {
            "month": month,
            "demand_level": get_seasonal_demand_level(month),
            "modifier": compute_seasonal_modifier(month),
        }

        policy_info = None
        try:
            from src.engine.policy import compute_policy_signal

            policy_info = await asyncio.to_thread(compute_policy_signal, _get_db_path())
        except Exception:
            pass

        from src.engine.llm_reasoning import generate_llm_report

        report = None
        try:
            report = await generate_llm_report(signal)
        except Exception:
            pass

        return templates.TemplateResponse(
            request,
            "partials/signal_card.html",
            context={
                "signal": signal,
                "gap": gap,
                "seasonal_info": seasonal_info,
                "policy_info": policy_info,
                "report": report,
            },
        )
    except Exception:
        return HTMLResponse(
            content='<div class="card-glow rounded-2xl bg-charcoal-700/60 border border-gold-500/15 p-8 text-center"><p class="text-charcoal-400 text-sm">Signal unavailable</p></div>',
            status_code=200,
        )


@router.get("/partials/prices")
async def get_prices_partial(request: Request):
    try:
        async with async_session() as session:
            prices = await get_latest_prices(session)

        if not prices:
            return templates.TemplateResponse(
                request,
                "partials/price_table.html",
                context={"dealers": []},
            )

        grouped: dict[str, dict] = defaultdict(
            lambda: {"source": "", "products": [], "fetched_at": None}
        )

        for p in prices:
            entry = grouped[p.source]
            entry["source"] = p.source

            if p.product_type == "xau_usd":
                product = {
                    "product_type": p.product_type,
                    "price_usd": p.price_usd,
                    "price_vnd": p.price_vnd,
                }
            else:
                product = {
                    "product_type": p.product_type,
                    "buy_price": p.buy_price,
                    "sell_price": p.sell_price,
                    "spread": p.spread,
                }

            entry["products"].append(product)
            if p.fetched_at:
                current = entry.get("_max_fetched_at")
                if current is None or p.fetched_at > current:
                    entry["_max_fetched_at"] = p.fetched_at

        for entry in grouped.values():
            raw = entry.pop("_max_fetched_at", None)
            if raw:
                vn_dt = (
                    raw.astimezone(VNTZ)
                    if raw.tzinfo
                    else raw.replace(tzinfo=timezone.utc).astimezone(VNTZ)
                )
                entry["fetched_at"] = vn_dt.isoformat()

        return templates.TemplateResponse(
            request,
            "partials/price_table.html",
            context={"dealers": list(grouped.values())},
        )
    except Exception:
        return HTMLResponse(
            content='<div class="card-glow rounded-2xl bg-charcoal-700/60 border border-gold-500/15 p-8 text-center"><p class="text-charcoal-400 text-sm">No price data available</p></div>',
            status_code=200,
        )


@router.get("/partials/gap")
async def get_gap_partial(request: Request):
    try:
        from src.analysis.gap import calculate_current_gap

        gap = await asyncio.to_thread(calculate_current_gap, _get_db_path())
        return templates.TemplateResponse(
            request,
            "partials/gap_display.html",
            context={"gap": gap},
        )
    except Exception:
        logging.getLogger(__name__).exception("Gap calculation failed")
        return templates.TemplateResponse(
            request,
            "partials/gap_display.html",
            context={"gap": None},
        )


@router.get("/partials/price-chart")
async def get_price_chart_partial(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/price_chart.html",
        context={},
    )


@router.get("/partials/gap-chart")
async def get_gap_chart_partial(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/gap_chart.html",
        context={},
    )


@router.get("/macro")
async def get_macro_data():
    db_path = _get_db_path()
    try:
        from src.analysis.macro import calculate_fx_trend, calculate_gold_trend

        fx_trend = await asyncio.to_thread(calculate_fx_trend, db_path)
        gold_trend = await asyncio.to_thread(calculate_gold_trend, db_path)

        dxy_value = None
        async with async_session() as session:
            from sqlalchemy import select
            from src.storage.models import PriceRecord

            stmt = (
                select(PriceRecord)
                .where(PriceRecord.product_type == "dxy")
                .order_by(PriceRecord.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record and record.price_usd:
                dxy_value = record.price_usd

        return {
            "fx_trend": fx_trend,
            "gold_trend": gold_trend,
            "dxy": dxy_value,
        }
    except Exception:
        return {"fx_trend": None, "gold_trend": None, "dxy": None}


@router.get("/partials/macro")
async def get_macro_partial(request: Request):
    try:
        db_path = _get_db_path()
        from src.analysis.macro import calculate_fx_trend, calculate_gold_trend

        fx_trend = await asyncio.to_thread(calculate_fx_trend, db_path)
        gold_trend = await asyncio.to_thread(calculate_gold_trend, db_path)

        dxy_value = None
        async with async_session() as session:
            from sqlalchemy import select
            from src.storage.models import PriceRecord

            stmt = (
                select(PriceRecord)
                .where(PriceRecord.product_type == "dxy")
                .order_by(PriceRecord.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record and record.price_usd:
                dxy_value = record.price_usd

        return templates.TemplateResponse(
            request,
            "partials/macro_card.html",
            context={
                "fx_trend": fx_trend,
                "gold_trend": gold_trend,
                "dxy": dxy_value,
            },
        )
    except Exception:
        return templates.TemplateResponse(
            request,
            "partials/macro_card.html",
            context={"fx_trend": None, "gold_trend": None, "dxy": None},
        )


@router.get("/news")
async def get_dashboard_news():
    try:
        async with async_session() as session:
            news = await get_recent_news(session, limit=15)

        return [
            {
                "id": n.id,
                "title": n.title,
                "url": n.url,
                "source": n.source,
                "published_at": n.published_at.isoformat() if n.published_at else None,
                "excerpt": n.excerpt,
                "category": n.category,
                "is_manual": n.is_manual,
            }
            for n in news
        ]
    except Exception:
        return []


@router.get("/partials/news")
async def get_news_partial(request: Request):
    try:
        async with async_session() as session:
            news = await get_recent_news(session, limit=15)

        return templates.TemplateResponse(
            request,
            "partials/news_card.html",
            context={"news_items": news},
        )
    except Exception:
        return templates.TemplateResponse(
            request,
            "partials/news_card.html",
            context={"news_items": []},
        )


@router.get("/report")
async def get_report_page(
    request: Request,
    mode: str = Query("saver", pattern="^(saver|trader)$"),
):
    from src.analysis.gap import (
        calculate_current_gap,
        calculate_historical_gaps,
        calculate_dealer_spreads,
        get_local_ring_gold_data,
    )
    from src.analysis.macro import calculate_fx_trend, calculate_gold_trend
    from src.engine.seasonal import get_seasonal_demand_level, get_month_name

    signal_mode = SignalMode(mode.upper())
    signal = await asyncio.to_thread(compute_signal, _get_db_path(), signal_mode)

    db_path = _get_db_path()

    current_gap = await asyncio.to_thread(calculate_current_gap, db_path)
    historical_gaps = await asyncio.to_thread(calculate_historical_gaps, db_path, "1M")
    dealer_spreads = await asyncio.to_thread(calculate_dealer_spreads, db_path)
    local_data = await asyncio.to_thread(get_local_ring_gold_data, db_path)
    fx_data = await asyncio.to_thread(calculate_fx_trend, db_path)
    gold_data = await asyncio.to_thread(calculate_gold_trend, db_path)

    month = datetime.now(timezone.utc).month
    seasonal_info = {
        "month": month,
        "demand_level": get_seasonal_demand_level(month),
        "month_name": get_month_name(month) if month else "",
    }

    policy_info = None
    try:
        from src.engine.policy import compute_policy_signal

        policy_info = await asyncio.to_thread(compute_policy_signal, db_path)
    except Exception:
        pass

    from src.engine.llm_reasoning import generate_llm_report

    report = None
    try:
        report = await generate_llm_report(
            signal,
            current_gap=current_gap,
            historical_gaps=historical_gaps or [],
            dealer_spreads=dealer_spreads,
            local_data=local_data,
            fx_data=fx_data,
            gold_data=gold_data,
            seasonal_info=seasonal_info,
            policy_info=policy_info,
        )
    except Exception:
        pass

    return templates.TemplateResponse(
        request,
        "report.html",
        context={
            "signal": signal,
            "current_gap": current_gap,
            "historical_gaps": historical_gaps or [],
            "dealer_spreads": dealer_spreads,
            "local_data": local_data,
            "fx_data": fx_data,
            "gold_data": gold_data,
            "seasonal_info": seasonal_info,
            "policy_info": policy_info,
            "mode": mode,
            "report": report,
        },
    )
