from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from src.storage.models import PolicyEvent


def compute_policy_signal(db_path: str) -> dict:
    engine = create_engine(f"sqlite:///{db_path}")
    now = datetime.now(timezone.utc)

    with Session(engine) as session:
        stmt = (
            select(PolicyEvent)
            .where(PolicyEvent.is_active.is_(True))
            .where(PolicyEvent.expires_at.is_(None) | (PolicyEvent.expires_at > now))
        )
        result = session.execute(stmt)
        events = list(result.scalars().all())

    if not events:
        return {
            "active_events": [],
            "has_override": False,
            "override_type": None,
            "confidence_cap": 1.0,
            "summary": "No active State Bank policy events",
        }

    max_severity = "low"
    override_impact = None
    descriptions = []

    for event in events:
        descriptions.append(event.description)
        severity_rank = {"low": 0, "medium": 1, "high": 2}
        if severity_rank.get(event.severity, 0) > severity_rank.get(max_severity, 0):
            max_severity = event.severity
        if event.severity in ("high", "medium") and override_impact is None:
            override_impact = event.impact

    has_override = max_severity in ("high", "medium")
    confidence_caps = {"high": 0.3, "medium": 0.6, "low": 1.0}
    confidence_cap = confidence_caps.get(max_severity, 1.0)

    summary_parts = [f"{len(events)} active policy event(s)"]
    if descriptions:
        summary_parts.append("; ".join(descriptions))
    if max_severity == "high":
        summary_parts.append(f"highest severity: {max_severity}")
    summary = ". ".join(summary_parts)

    return {
        "active_events": events,
        "has_override": has_override,
        "override_type": override_impact if has_override else None,
        "confidence_cap": confidence_cap,
        "summary": summary,
    }
