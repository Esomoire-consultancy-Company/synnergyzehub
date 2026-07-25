from datetime import datetime, timezone

from app.riveros_search import plan_search


def test_plans_structured_filters_and_keeps_remaining_text():
    now = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)
    plan = plan_search(
        "11111111-1111-1111-1111-111111111111",
        "show settlement eligible agent events last 7 days limit 20 invoice",
        now=now,
    )

    assert plan.actor_type == "agent"
    assert plan.settlement_eligibility == "eligible"
    assert plan.occurred_after == "2026-07-18T12:00:00+00:00"
    assert plan.occurred_before == "2026-07-25T12:00:00+00:00"
    assert plan.text_query == "invoice"
    assert plan.limit == 20


def test_requires_delivery_scope_inputs():
    plan = plan_search(
        "11111111-1111-1111-1111-111111111111",
        "event type PAYMENT_EVENT_RECORDED accepted commercially relevant",
    )

    assert plan.event_type == "PAYMENT_EVENT_RECORDED"
    assert plan.lifecycle_status == "ACCEPTED"
    assert plan.commercial_relevance is True
    assert plan.text_query is None


def test_caps_limit_at_200():
    plan = plan_search(
        "11111111-1111-1111-1111-111111111111",
        "show first 999 events",
    )

    assert plan.limit == 200
