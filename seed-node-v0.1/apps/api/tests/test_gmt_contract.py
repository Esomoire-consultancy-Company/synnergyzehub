import os
import unittest
from unittest.mock import Mock
from uuid import UUID

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql://synnergyze:test@localhost:5432/synnergyze_seed",
)

from fastapi import HTTPException

from app import gmt
from app.main import app


class GrowMyTradeContractTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("DIGITALME_TRUSTED_INGRESS", None)

    def test_digitalme_ingress_fails_closed(self):
        with self.assertRaises(HTTPException) as ctx:
            gmt._require_trusted_context("dm:test", "proof:test", "user-test")
        self.assertEqual(ctx.exception.status_code, 503)

    def test_trusted_context_requires_actor_binding(self):
        os.environ["DIGITALME_TRUSTED_INGRESS"] = "true"
        with self.assertRaises(HTTPException) as ctx:
            gmt._require_trusted_context("dm:test", "proof:test", None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_request_hash_is_deterministic(self):
        first = gmt._payload_hash({"b": 2, "a": 1})
        second = gmt._payload_hash({"a": 1, "b": 2})
        self.assertEqual(first, second)

    def test_idempotency_key_cannot_be_reused_for_another_case(self):
        cur = Mock()
        cur.fetchone.return_value = {
            "request_hash": "same-request",
            "case_id": UUID("00000000-0000-0000-0000-000000000001"),
        }

        with self.assertRaises(HTTPException) as ctx:
            gmt._check_idempotency(
                cur,
                workspace_id="workspace",
                case_id="00000000-0000-0000-0000-000000000002",
                scope="business-discovery",
                idempotency_key="request-key",
                request_hash="same-request",
            )

        self.assertEqual(ctx.exception.status_code, 409)
        cur.execute.assert_called_once()

    def test_idempotency_replay_matches_uuid_formatting(self):
        cur = Mock()
        cur.fetchone.side_effect = [
            {
                "request_hash": "same-request",
                "case_id": UUID("00000000-0000-0000-0000-000000000001"),
            },
            {"exists": 1},
        ]

        replayed = gmt._check_idempotency(
            cur,
            workspace_id="workspace",
            case_id="00000000000000000000000000000001",
            scope="business-discovery",
            idempotency_key="request-key",
            request_hash="same-request",
        )

        self.assertTrue(replayed)

    def test_independent_business_rights_are_preserved(self):
        self.assertTrue(gmt.RIGHTS_CONTEXT["business_ownership_retained"])
        self.assertTrue(gmt.RIGHTS_CONTEXT["customer_relationships_not_assigned"])
        self.assertTrue(gmt.RIGHTS_CONTEXT["non_contributed_ip_retained"])
        self.assertTrue(gmt.RIGHTS_CONTEXT["commercial_autonomy_retained"])
        self.assertTrue(gmt.RIGHTS_CONTEXT["commons_membership_separate_opt_in"])
        self.assertTrue(gmt.RIGHTS_CONTEXT["no_warden_authority_implied_by_onboarding"])

    def test_gmt_routes_are_registered(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/gmt/onboarding-cases", paths)
        self.assertIn("/gmt/onboarding-cases/{case_id}/discovery", paths)
        self.assertIn("/gmt/onboarding-cases/{case_id}/plan", paths)
        self.assertIn("/gmt/onboarding-cases/{case_id}/participant-approval", paths)

    def test_r0_1_exposes_no_trade_or_settlement_route(self):
        paths = {route.path for route in app.routes if route.path.startswith("/gmt/")}
        forbidden_fragments = ("trade", "payment", "settlement", "silk", "wallet")
        for path in paths:
            for fragment in forbidden_fragments:
                self.assertNotIn(fragment, path.lower())


if __name__ == "__main__":
    unittest.main()
