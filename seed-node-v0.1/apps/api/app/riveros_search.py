from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from typing import Any


_ALLOWED_STATUSES = {
    "RECEIVED", "VALIDATING", "VERIFIED", "ACCEPTED", "APPLIED",
    "SETTLEMENT_ELIGIBLE", "CLOSED", "REJECTED", "QUARANTINED",
    "DISPUTED", "SUSPENDED", "REVERSED", "SUPERSEDED",
}
_ALLOWED_SETTLEMENT = {"not_applicable", "not_eligible", "pending", "eligible", "revoked"}


@dataclass(frozen=True)
class SearchPlan:
    workspace_id: str
    original_query: str
    event_type: str | None = None
    lifecycle_status: str | None = None
    object_type: str | None = None
    actor_type: str | None = None
    settlement_eligibility: str | None = None
    commercial_relevance: bool | None = None
    occurred_after: str | None = None
    occurred_before: str | None = None
    text_query: str | None = None
    limit: int = 50
    order: str = "occurred_at_desc"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def sql_parameters(self) -> tuple[Any, ...]:
        return (
            self.workspace_id,
            self.event_type,
            self.lifecycle_status,
            self.object_type,
            self.actor_type,
            self.settlement_eligibility,
            self.commercial_relevance,
            self.occurred_after,
            self.occurred_before,
            self.text_query,
            self.limit,
        )


def _extract_time_window(query: str, now: datetime) -> tuple[str | None, str | None, str]:
    patterns = [
        (r"\b(?:last|past)\s+(\d+)\s+hours?\b", "hours"),
        (r"\b(?:last|past)\s+(\d+)\s+days?\b", "days"),
        (r"\b(?:last|past)\s+(\d+)\s+weeks?\b", "weeks"),
    ]
    for pattern, unit in patterns:
        match = re.search(pattern, query, flags=re.IGNORECASE)
        if match:
            amount = min(int(match.group(1)), 3650)
            delta = timedelta(**{unit: amount})
            cleaned = (query[: match.start()] + " " + query[match.end() :]).strip()
            return (now - delta).isoformat(), now.isoformat(), cleaned

    if re.search(r"\btoday\b", query, flags=re.IGNORECASE):
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        cleaned = re.sub(r"\btoday\b", " ", query, flags=re.IGNORECASE).strip()
        return start.isoformat(), now.isoformat(), cleaned

    return None, None, query


def _consume_phrase(query: str, pattern: str) -> tuple[bool, str]:
    match = re.search(pattern, query, flags=re.IGNORECASE)
    if not match:
        return False, query
    return True, (query[: match.start()] + " " + query[match.end() :]).strip()


def plan_search(workspace_id: str, query: str, *, now: datetime | None = None, default_limit: int = 50) -> SearchPlan:
    if not workspace_id.strip():
        raise ValueError("workspace_id is required")
    if not query.strip():
        raise ValueError("query is required")

    now = now or datetime.now(timezone.utc)
    working = " ".join(query.strip().split())
    occurred_after, occurred_before, working = _extract_time_window(working, now)

    limit = default_limit
    limit_match = re.search(r"\b(?:limit|top|first)\s+(\d+)\b", working, flags=re.IGNORECASE)
    if limit_match:
        limit = max(1, min(int(limit_match.group(1)), 200))
        working = (working[: limit_match.start()] + " " + working[limit_match.end() :]).strip()

    lifecycle_status = None
    for status in sorted(_ALLOWED_STATUSES, key=len, reverse=True):
        phrase = status.lower().replace("_", r"[\s_-]")
        found, working = _consume_phrase(working, rf"\b{phrase}\b")
        if found:
            lifecycle_status = status
            break

    settlement_eligibility = None
    settlement_aliases = {
        "settlement eligible": "eligible",
        "eligible for settlement": "eligible",
        "settlement pending": "pending",
        "settlement revoked": "revoked",
        "not settlement eligible": "not_eligible",
    }
    for phrase, value in settlement_aliases.items():
        found, working = _consume_phrase(working, rf"\b{re.escape(phrase)}\b")
        if found:
            settlement_eligibility = value
            break

    commercial_relevance = None
    found, working = _consume_phrase(working, r"\bcommercial(?:ly)?\s+relevant\b")
    if found:
        commercial_relevance = True
    else:
        found, working = _consume_phrase(working, r"\bnon[-\s]?commercial\b")
        if found:
            commercial_relevance = False

    actor_type = None
    for candidate in ("agent", "user", "device", "system", "service"):
        found, working = _consume_phrase(working, rf"\b{candidate}\s+events?\b")
        if found:
            actor_type = candidate
            break

    event_type = None
    event_match = re.search(r"\bevent\s+type\s+([A-Za-z0-9_.:-]+)\b", working, flags=re.IGNORECASE)
    if event_match:
        event_type = event_match.group(1).upper()
        working = (working[: event_match.start()] + " " + working[event_match.end() :]).strip()

    object_type = None
    object_match = re.search(r"\b(?:object|for)\s+type\s+([A-Za-z0-9_.:-]+)\b", working, flags=re.IGNORECASE)
    if object_match:
        object_type = object_match.group(1).lower()
        working = (working[: object_match.start()] + " " + working[object_match.end() :]).strip()

    noise = r"\b(?:show|find|search|list|give|me|all|the|events?|records?|where|with|and|that|are|is)\b"
    text_query = " ".join(re.sub(noise, " ", working, flags=re.IGNORECASE).split()) or None

    return SearchPlan(
        workspace_id=workspace_id,
        original_query=query,
        event_type=event_type,
        lifecycle_status=lifecycle_status,
        object_type=object_type,
        actor_type=actor_type,
        settlement_eligibility=settlement_eligibility,
        commercial_relevance=commercial_relevance,
        occurred_after=occurred_after,
        occurred_before=occurred_before,
        text_query=text_query,
        limit=limit,
    )


SEARCH_SQL = """
SELECT *
FROM riveros.search_events(
    %s::uuid,
    %s::text,
    %s::text,
    %s::text,
    %s::text,
    %s::text,
    %s::boolean,
    %s::timestamptz,
    %s::timestamptz,
    %s::text,
    %s::integer
)
"""
