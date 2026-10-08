import unittest
from datetime import datetime, timezone

from app.riveros_search import plan_search


class RiverOSSearchPlannerTests(unittest.TestCase):
    def test_plans_structured_filters_and_keeps_remaining_text(self):
        now = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)
        plan = plan_search(
            "11111111-1111-1111-1111-111111111111",
            "show settlement eligible agent events last 7 days limit 20 invoice",
            now=now,
        )

        self.assertEqual(plan.actor_type, "agent")
        self.assertEqual(plan.settlement_eligibility, "eligible")
        self.assertEqual(plan.occurred_after, "2026-07-18T12:00:00+00:00")
        self.assertEqual(plan.occurred_before, "2026-07-25T12:00:00+00:00")
        self.assertEqual(plan.text_query, "invoice")
        self.assertEqual(plan.limit, 20)

    def test_plans_event_filters(self):
        plan = plan_search(
            "11111111-1111-1111-1111-111111111111",
            "event type PAYMENT_EVENT_RECORDED accepted commercially relevant",
        )

        self.assertEqual(plan.event_type, "PAYMENT_EVENT_RECORDED")
        self.assertEqual(plan.lifecycle_status, "ACCEPTED")
        self.assertTrue(plan.commercial_relevance)
        self.assertIsNone(plan.text_query)

    def test_caps_limit_at_200(self):
        plan = plan_search(
            "11111111-1111-1111-1111-111111111111",
            "show first 999 events",
        )

        self.assertEqual(plan.limit, 200)


if __name__ == "__main__":
    unittest.main()
