import hashlib
import hmac
import json
import os
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

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
        os.environ.pop("DIGITALME_TRUSTED_INGRESS_SECRET", None)

    def test_digitalme_ingress_fails_closed(self):
        with self.assertRaises(HTTPException) as ctx:
            gmt._require_trusted_context("dm:test", "proof:test", "user-test")
        self.assertEqual(ctx.exception.status_code, 503)

    def test_trusted_context_requires_actor_binding(self):
        os.environ["DIGITALME_TRUSTED_INGRESS"] = "true"
        with self.assertRaises(HTTPException) as ctx:
            gmt._require_trusted_context("dm:test", "proof:test", None)
        self.assertEqual(ctx.exception.status_code, 401)

    def test_trusted_context_requires_authenticated_assertion(self):
        os.environ["DIGITALME_TRUSTED_INGRESS"] = "true"
        os.environ["DIGITALME_TRUSTED_INGRESS_SECRET"] = "a" * 32
        actor_user_id = str(uuid4())
        payload = json.dumps(
            ["dm:test", "proof:test", actor_user_id], separators=(",", ":")
        ).encode("utf-8")
        assertion = hmac.new(        b"a" * 32, payload, hashlib.sha256).hexdigest()

        self.assertEqual(
            gmt._require_trusted_context(
                "dm:test", "proof:test", actor_user_id, assertion
            ),
            ("dm:test", "proof:test", actor_user_id),
        )
        with self.assertRaises(HTTPException) as ctx:
            gmt._require_trusted_context(
                "dm:test", "proof:test", actor_user_id, "untrusted"
            )
        self.assertEqual(ctx.exception.status_code, 401)
        with self.assertRaises(HTTPException) as ctx:
            gmt._require_trusted_context(
                "dm:test", "proof:test", actor_user_id, "not-ascii-🔑"
            )
        self.assertEqual(ctx.exception.status_code, 401)

    def test_identifiers_are_validated_and_normalized_as_uuids(self):
        value = str(uuid4())
        self.assertEqual(gmt._normalize_uuid(value.upper(), "case_id"), value)
        with self.assertRaises(HTTPException) as ctx:
            gmt._normalize_uuid("not-a-uuid", "case_id")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_mutation_case_lookup_locks_row(self):
        cur = Mock()
        cur.fetchone.side_effect = [
            {"id": str(uuid4()), "workspace_id": str(uuid4()), "state": "PLAN_READY"},
            {"active": True},
        ]
        case_id = str(uuid4())
        gmt._load_case(cur, case_id, "dm:test", str(uuid4()), for_update=True)
        self.assertIn("FOR UPDATE", cur.execute.call_args_list[0].args[0])

    def test_concurrent_case_creation_replays_winner_without_emitting_event(self):
        os.environ["DIGITALME_TRUSTED_INGRESS"] = "true"
        os.environ["DIGITALME_TRUSTED_INGRESS_SECRET"] = "a" * 32
        workspace_id = str(uuid4())
        actor_user_id = str(uuid4())
        signed_context = json.dumps(
            ["dm:test", "proof:test", actor_user_id], separators=(",", ":")
        ).encode("utf-8")
        assertion = hmac.new(
            b"a" * 32, signed_context, hashlib.sha256
        ).hexdigest()
        winner = {
            "id": str(uuid4()),
            "workspace_id": workspace_id,
            "actor_user_id": actor_user_id,
            "digitalme_principal": "dm:test",
        }
        cur = Mock()
        cur.fetchone.side_effect = [{"member": True}, None, None, winner]
        cur.__enter__ = Mock(return_value=cur)
        cur.__exit__ = Mock(return_value=False)
        conn = Mock()
        conn.cursor.return_value = cur
        conn.__enter__ = Mock(return_value=conn)
        conn.__exit__ = Mock(return_value=False)

        with patch.object(gmt, "get_conn", return_value=conn):
            case = gmt.create_onboarding_case(
                gmt.OnboardingCreate(
                    workspace_id=workspace_id, rights_acknowledged=True
                ),
                "create-key",
                "dm:test",
                "proof:test",
                actor_user_id,
                assertion,
            )

        self.assertEqual(case, winner)
        self.assertIn(
            "ON CONFLICT (workspace_id, create_idempotency_key) DO NOTHING",
            cur.execute.call_args_list[2].args[0],
        )
        self.assertFalse(
            any("INSERT INTO riveros.events" in call.args[0] for call in cur.execute.call_args_list)
        )

    def test_idempotency_key_cannot_be_reused_for_another_case(self):
        cur = Mock()
        cur.fetchone.return_value = {
            "case_id": str(uuid4()),
            "request_hash": "same-request",
        }
        with self.assertRaises(HTTPException) as ctx:
            gmt._check_idempotency(
                cur,
                workspace_id=str(uuid4()),
                case_id=str(uuid4()),
                scope="business-plan",
                idempotency_key="retry",
                request_hash="same-request",
            )
        self.assertEqual(ctx.exception.status_code, 409)

    def test_riveros_event_uses_partial_index_conflict_predicate(self):
        cur = Mock()
        gmt._emit_river_event(
            cur,
            workspace_id=str(uuid4()),
            actor_user_id=str(uuid4()),
            principal="dm:test",
            object_id=str(uuid4()),
            action="test",
            event_type="GMT_TEST",
            idempotency_key="event-key",
            previous_state=None,
            new_state={"state": "IDENTITY_VERIFIED"},
            verification_ref="proof:test",
        )
        self.assertIn(
            "WHERE idempotency_key IS NOT NULL",
            cur.execute.call_args.args[0],
        )

    def test_request_hash_is_deterministic(self):
        first = gmt._payload_hash({"b": 2, "a": 1})
        second = gmt._payload_hash({"a": 1, "b": 2})
        self.assertEqual(first, second)

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
