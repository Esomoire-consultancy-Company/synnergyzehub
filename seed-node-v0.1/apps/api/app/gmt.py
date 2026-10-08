import hashlib
import hmac
import json
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from app.db import get_conn


router = APIRouter(prefix="/gmt", tags=["grow-my-trade"])

WORKFLOW_ID = "VSR-GMT-SYN-ONBOARD-001"
RIGHTS_VERSION = "GMT-INDEPENDENT-BUSINESS-RIGHTS-R0.1"
SOURCE_SYSTEM = "synnergyze-grow-my-trade"

RIGHTS_CONTEXT = {
    "business_ownership_retained": True,
    "customer_relationships_not_assigned": True,
    "non_contributed_ip_retained": True,
    "commercial_autonomy_retained": True,
    "banking_and_tax_remain_business_responsibility": True,
    "commons_membership_separate_opt_in": True,
    "no_warden_authority_implied_by_onboarding": True,
}


class OnboardingCreate(BaseModel):
    workspace_id: str
    rights_acknowledged: bool


class DiscoverySubmit(BaseModel):
    legal_name: str
    trade_name: str | None = None
    business_type: str
    sector: str
    legacy_role: str | None = None
    declared_supplier_count: int = Field(default=0, ge=0)
    declared_buyer_count: int = Field(default=0, ge=0)
    declared_service_provider_count: int = Field(default=0, ge=0)
    capability_claims: list[str] = Field(default_factory=list)
    future_business_goal: str | None = None


class PlanRecord(BaseModel):
    proposed_business_model: str
    operating_scope: str | None = None
    capability_gaps: list[str] = Field(default_factory=list)
    notes: str | None = None


class ParticipantApproval(BaseModel):
    accepted: bool


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload_hash(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _normalize_uuid(value: str, field: str) -> str:
    try:
        return str(UUID(value))
    except (AttributeError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail=f"{field} must be a valid UUID.")


def _require_trusted_context(
    principal: str | None,
    verification_ref: str | None,
    actor_user_id: str | None,
    assertion: str | None = None,
) -> tuple[str, str, str]:
    # R0.1 does not implement an identity-verification engine.
    # It accepts identity only from a trusted upstream VSR/DigitalMe ingress and
    # defaults to fail-closed so development headers cannot be mistaken for proof.
    if os.getenv("DIGITALME_TRUSTED_INGRESS", "").lower() != "true":
        raise HTTPException(
            status_code=503,
            detail="DigitalMe trusted ingress is not enabled; onboarding remains on HOLD.",
        )
    if not principal or not verification_ref or not actor_user_id:
        raise HTTPException(
            status_code=401,
            detail=(
                "Verified DigitalMe principal, verification reference, and "
                "workspace actor user are required."
            ),
        )
    actor_user_id = _normalize_uuid(actor_user_id, "actor_user_id")
    secret = os.getenv("DIGITALME_TRUSTED_INGRESS_SECRET")
    if not secret or len(secret.encode("utf-8")) < 32:
        raise HTTPException(
            status_code=503,
            detail="DigitalMe trusted ingress requires a secret of at least 32 bytes.",
        )
    assertion_payload = json.dumps(
        [principal, verification_ref, actor_user_id], separators=(",", ":")
    ).encode("utf-8")
    expected_assertion = hmac.new(
        secret.encode("utf-8"), assertion_payload, hashlib.sha256
    ).hexdigest()
    if not assertion or not hmac.compare_digest(
        assertion.encode("utf-8"), expected_assertion.encode("ascii")
    ):
        raise HTTPException(
            status_code=401,
            detail="DigitalMe trusted ingress assertion is invalid.",
        )
    return principal, verification_ref, actor_user_id


def _require_workspace_membership(cur, workspace_id: str, actor_user_id: str):
    workspace_id = _normalize_uuid(workspace_id, "workspace_id")
    actor_user_id = _normalize_uuid(actor_user_id, "actor_user_id")
    cur.execute(
        """
        SELECT 1
          FROM workspace.members
         WHERE workspace_id = %s
           AND user_id = %s
           AND status = 'active'
         LIMIT 1
        """,
        (workspace_id, actor_user_id),
    )
    if not cur.fetchone():
        raise HTTPException(
            status_code=403,
            detail="The verified actor is not an active member of this workspace.",
        )


def _load_case(
    cur, case_id: str, principal: str, actor_user_id: str, *, for_update: bool = False
):
    case_id = _normalize_uuid(case_id, "case_id")
    actor_user_id = _normalize_uuid(actor_user_id, "actor_user_id")
    lock_clause = "FOR UPDATE" if for_update else ""
    cur.execute(
        f"""
        SELECT *
          FROM gmt.onboarding_cases
         WHERE id = %s
           AND digitalme_principal = %s
           AND actor_user_id = %s
         {lock_clause}
        """,
        (case_id, principal, actor_user_id),
    )
    case = cur.fetchone()
    if not case:
        raise HTTPException(status_code=404, detail="Onboarding case not found.")
    _require_workspace_membership(cur, str(case["workspace_id"]), actor_user_id)
    return case


def _require_state(case, allowed: set[str]):
    if case["state"] not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Transition not allowed from state {case['state']}.",
        )


def _check_idempotency(
    cur,
    *,
    workspace_id: str,
    case_id: str,
    scope: str,
    idempotency_key: str,
    request_hash: str,
) -> bool:
    cur.execute(
        """
        SELECT case_id, request_hash
          FROM gmt.idempotency_records
         WHERE workspace_id = %s
           AND scope = %s
           AND idempotency_key = %s
        """,
        (workspace_id, scope, idempotency_key),
    )
    record = cur.fetchone()
    if not record:
        return False
    if str(record["case_id"]) != case_id:
        raise HTTPException(
            status_code=409,
            detail="Idempotency key belongs to a different onboarding case.",
        )
    if record["request_hash"] != request_hash:
        raise HTTPException(
            status_code=409,
            detail="Idempotency key was already used with a different request.",
        )
    return True


def _lock_idempotency_key(cur, workspace_id: str, scope: str, idempotency_key: str):
    cur.execute(
        "SELECT pg_advisory_xact_lock(hashtext(%s), hashtext(%s))",
        (workspace_id, f"{scope}:{idempotency_key}"),
    )


def _record_idempotency(
    cur,
    *,
    workspace_id: str,
    case_id: str,
    scope: str,
    idempotency_key: str,
    request_hash: str,
    resulting_state: str,
):
    cur.execute(
        """
        INSERT INTO gmt.idempotency_records (
          workspace_id,
          case_id,
          scope,
          idempotency_key,
          request_hash,
          resulting_state
        ) VALUES (%s,%s,%s,%s,%s,%s)
        """,
        (
            workspace_id,
            case_id,
            scope,
            idempotency_key,
            request_hash,
            resulting_state,
        ),
    )


def _emit_river_event(
    cur,
    *,
    workspace_id: str,
    actor_user_id: str,
    principal: str,
    object_id: str,
    action: str,
    event_type: str,
    idempotency_key: str,
    previous_state: dict | None,
    new_state: dict | None,
    verification_ref: str,
    consent_context: dict | None = None,
):
    cur.execute(
        """
        INSERT INTO riveros.events (
          workspace_id,
          event_type,
          event_version,
          action,
          source_system,
          source_environment,
          idempotency_key,
          actor_type,
          actor_user_id,
          digitalme_principal,
          object_type,
          object_id,
          workflow_id,
          previous_state,
          new_state,
          authority_basis,
          consent_context,
          commercial_relevance,
          settlement_eligibility,
          lifecycle_status,
          occurred_at,
          metadata
        ) VALUES (
          %s,%s,'0.2',%s,%s,%s,%s,
          'user',%s,%s,'gmt_onboarding_case',%s,%s,
          %s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,
          FALSE,'not_applicable','APPLIED',NOW(),%s::jsonb
        )
        ON CONFLICT (workspace_id, source_system, idempotency_key)
          WHERE idempotency_key IS NOT NULL
        DO NOTHING
        """,
        (
            workspace_id,
            event_type,
            action,
            SOURCE_SYSTEM,
            os.getenv("ENVIRONMENT", "development"),
            idempotency_key,
            actor_user_id,
            principal,
            object_id,
            WORKFLOW_ID,
            json.dumps(previous_state) if previous_state is not None else None,
            json.dumps(new_state) if new_state is not None else None,
            json.dumps(
                {
                    "digitalme_verification_ref": verification_ref,
                    "warden_authority": None,
                    "note": (
                        "Grow My Trade R0.1 discovery only; "
                        "no protected execution authority granted."
                    ),
                }
            ),
            json.dumps(consent_context or {}),
            json.dumps(
                {
                    "workflow_revision": "R0.1",
                    "independent_business_rights_version": RIGHTS_VERSION,
                }
            ),
        ),
    )


@router.post("/onboarding-cases")
def create_onboarding_case(
    payload: OnboardingCreate,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    x_digitalme_principal: str | None = Header(None, alias="X-DigitalMe-Principal"),
    x_digitalme_verification_ref: str | None = Header(
        None, alias="X-DigitalMe-Verification-Ref"
    ),
    x_actor_user_id: str | None = Header(None, alias="X-Actor-User-Id"),
    x_digitalme_assertion: str | None = Header(None, alias="X-DigitalMe-Assertion"),
):
    principal, verification_ref, actor_user_id = _require_trusted_context(
        x_digitalme_principal,
        x_digitalme_verification_ref,
        x_actor_user_id,
        x_digitalme_assertion,
    )
    workspace_id = _normalize_uuid(payload.workspace_id, "workspace_id")
    if not payload.rights_acknowledged:
        raise HTTPException(
            status_code=400,
            detail="Independent business rights must be acknowledged before onboarding.",
        )

    with get_conn() as conn:
        with conn.cursor() as cur:
            _require_workspace_membership(cur, workspace_id, actor_user_id)

            cur.execute(
                """
                SELECT *
                  FROM gmt.onboarding_cases
                 WHERE workspace_id = %s
                   AND create_idempotency_key = %s
                """,
                (workspace_id, x_idempotency_key),
            )
            existing = cur.fetchone()
            if existing:
                if (
                    existing["digitalme_principal"] != principal
                    or str(existing["actor_user_id"]) != actor_user_id
                ):
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency key belongs to a different verified actor.",
                    )
                return existing

            cur.execute(
                """
                INSERT INTO gmt.onboarding_cases (
                  workspace_id,
                  actor_user_id,
                  digitalme_principal,
                  digitalme_verification_ref,
                  state,
                  rights_version,
                  rights_context,
                  rights_acknowledged_at,
                  create_idempotency_key
                ) VALUES (
                  %s,%s,%s,%s,'IDENTITY_VERIFIED',%s,%s::jsonb,NOW(),%s
                )
                ON CONFLICT (workspace_id, create_idempotency_key) DO NOTHING
                RETURNING *
                """,
                (
                    workspace_id,
                    actor_user_id,
                    principal,
                    verification_ref,
                    RIGHTS_VERSION,
                    json.dumps(RIGHTS_CONTEXT),
                    x_idempotency_key,
                ),
            )
            case = cur.fetchone()
            if case is None:
                cur.execute(
                    """
                    SELECT *
                      FROM gmt.onboarding_cases
                     WHERE workspace_id = %s
                       AND create_idempotency_key = %s
                    """,
                    (workspace_id, x_idempotency_key),
                )
                case = cur.fetchone()
                if not case:
                    raise HTTPException(
                        status_code=409,
                        detail="Unable to resolve the winning onboarding case.",
                    )
                if (
                    case["digitalme_principal"] != principal
                    or str(case["actor_user_id"]) != actor_user_id
                ):
                    raise HTTPException(
                        status_code=409,
                        detail="Idempotency key belongs to a different verified actor.",
                    )
                return case

            _emit_river_event(
                cur,
                workspace_id=workspace_id,
                actor_user_id=actor_user_id,
                principal=principal,
                object_id=str(case["id"]),
                action="create_onboarding_case",
                event_type="GMT_ONBOARDING_CASE_CREATED",
                idempotency_key=f"{x_idempotency_key}:case-created",
                previous_state=None,
                new_state={"state": "IDENTITY_VERIFIED"},
                verification_ref=verification_ref,
                consent_context={
                    "rights_acknowledged": True,
                    "rights_version": RIGHTS_VERSION,
                },
            )
        conn.commit()
    return case


@router.post("/onboarding-cases/{case_id}/discovery")
def submit_discovery(
    case_id: str,
    payload: DiscoverySubmit,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    x_digitalme_principal: str | None = Header(None, alias="X-DigitalMe-Principal"),
    x_digitalme_verification_ref: str | None = Header(
        None, alias="X-DigitalMe-Verification-Ref"
    ),
    x_actor_user_id: str | None = Header(None, alias="X-Actor-User-Id"),
    x_digitalme_assertion: str | None = Header(None, alias="X-DigitalMe-Assertion"),
):
    principal, verification_ref, actor_user_id = _require_trusted_context(
        x_digitalme_principal,
        x_digitalme_verification_ref,
        x_actor_user_id,
        x_digitalme_assertion,
    )
    case_id = _normalize_uuid(case_id, "case_id")
    request_hash = _payload_hash(payload.model_dump())

    business_declaration = {
        "legal_name": payload.legal_name,
        "trade_name": payload.trade_name,
        "business_type": payload.business_type,
        "sector": payload.sector,
        "legacy_role": payload.legacy_role,
        "future_business_goal": payload.future_business_goal,
    }
    network_summary = {
        "declared_supplier_count": payload.declared_supplier_count,
        "declared_buyer_count": payload.declared_buyer_count,
        "declared_service_provider_count": payload.declared_service_provider_count,
        "counterparty_identity_storage": "not_collected_r0.1",
        "disclosure": "private_summary_only",
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            case = _load_case(cur, case_id, principal, actor_user_id, for_update=True)
            _lock_idempotency_key(
                cur, str(case["workspace_id"]), "business-discovery", x_idempotency_key
            )
            if _check_idempotency(
                cur,
                workspace_id=str(case["workspace_id"]),
                case_id=case_id,
                scope="business-discovery",
                idempotency_key=x_idempotency_key,
                request_hash=request_hash,
            ):
                return case

            _require_state(case, {"IDENTITY_VERIFIED", "BUSINESS_DECLARED"})
            previous = {"state": case["state"]}

            cur.execute(
                """
                UPDATE gmt.onboarding_cases
                   SET business_declaration = %s::jsonb,
                       network_summary = %s::jsonb,
                       capability_claims = %s::jsonb,
                       state = 'BUSINESS_DECLARED',
                       updated_at = NOW()
                 WHERE id = %s
                 RETURNING *
                """,
                (
                    json.dumps(business_declaration),
                    json.dumps(network_summary),
                    json.dumps(payload.capability_claims),
                    case_id,
                ),
            )
            updated = cur.fetchone()

            _record_idempotency(
                cur,
                workspace_id=str(updated["workspace_id"]),
                case_id=case_id,
                scope="business-discovery",
                idempotency_key=x_idempotency_key,
                request_hash=request_hash,
                resulting_state="BUSINESS_DECLARED",
            )
            _emit_river_event(
                cur,
                workspace_id=str(updated["workspace_id"]),
                actor_user_id=actor_user_id,
                principal=principal,
                object_id=case_id,
                action="submit_business_discovery",
                event_type="GMT_BUSINESS_DISCOVERY_RECORDED",
                idempotency_key=f"{x_idempotency_key}:business-discovery",
                previous_state=previous,
                new_state={"state": "BUSINESS_DECLARED"},
                verification_ref=verification_ref,
                consent_context={
                    "network_disclosure": "private_summary_only",
                    "counterparty_identity_storage": "not_collected_r0.1",
                },
            )
        conn.commit()
    return updated


@router.post("/onboarding-cases/{case_id}/plan")
def record_plan(
    case_id: str,
    payload: PlanRecord,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    x_digitalme_principal: str | None = Header(None, alias="X-DigitalMe-Principal"),
    x_digitalme_verification_ref: str | None = Header(
        None, alias="X-DigitalMe-Verification-Ref"
    ),
    x_actor_user_id: str | None = Header(None, alias="X-Actor-User-Id"),
    x_digitalme_assertion: str | None = Header(None, alias="X-DigitalMe-Assertion"),
):
    principal, verification_ref, actor_user_id = _require_trusted_context(
        x_digitalme_principal,
        x_digitalme_verification_ref,
        x_actor_user_id,
        x_digitalme_assertion,
    )
    case_id = _normalize_uuid(case_id, "case_id")
    request_hash = _payload_hash(payload.model_dump())

    plan = {
        "status": "draft",
        "source": "synnergyze",
        "proposed_business_model": payload.proposed_business_model,
        "operating_scope": payload.operating_scope,
        "capability_gaps": payload.capability_gaps,
        "notes": payload.notes,
        "authority_effect": "none",
        "generated_or_recorded_at": _now_iso(),
    }

    with get_conn() as conn:
        with conn.cursor() as cur:
            case = _load_case(cur, case_id, principal, actor_user_id, for_update=True)
            _lock_idempotency_key(
                cur, str(case["workspace_id"]), "business-plan", x_idempotency_key
            )
            if _check_idempotency(
                cur,
                workspace_id=str(case["workspace_id"]),
                case_id=case_id,
                scope="business-plan",
                idempotency_key=x_idempotency_key,
                request_hash=request_hash,
            ):
                return case

            _require_state(case, {"BUSINESS_DECLARED", "PLAN_READY"})
            previous = {"state": case["state"]}

            cur.execute(
                """
                UPDATE gmt.onboarding_cases
                   SET business_plan = %s::jsonb,
                       state = 'PLAN_READY',
                       updated_at = NOW()
                 WHERE id = %s
                 RETURNING *
                """,
                (json.dumps(plan), case_id),
            )
            updated = cur.fetchone()

            _record_idempotency(
                cur,
                workspace_id=str(updated["workspace_id"]),
                case_id=case_id,
                scope="business-plan",
                idempotency_key=x_idempotency_key,
                request_hash=request_hash,
                resulting_state="PLAN_READY",
            )
            _emit_river_event(
                cur,
                workspace_id=str(updated["workspace_id"]),
                actor_user_id=actor_user_id,
                principal=principal,
                object_id=case_id,
                action="record_synnergyze_plan",
                event_type="GMT_BUSINESS_PLAN_READY",
                idempotency_key=f"{x_idempotency_key}:plan-ready",
                previous_state=previous,
                new_state={"state": "PLAN_READY"},
                verification_ref=verification_ref,
            )
        conn.commit()
    return updated


@router.post("/onboarding-cases/{case_id}/participant-approval")
def participant_approval(
    case_id: str,
    payload: ParticipantApproval,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    x_digitalme_principal: str | None = Header(None, alias="X-DigitalMe-Principal"),
    x_digitalme_verification_ref: str | None = Header(
        None, alias="X-DigitalMe-Verification-Ref"
    ),
    x_actor_user_id: str | None = Header(None, alias="X-Actor-User-Id"),
    x_digitalme_assertion: str | None = Header(None, alias="X-DigitalMe-Assertion"),
):
    principal, verification_ref, actor_user_id = _require_trusted_context(
        x_digitalme_principal,
        x_digitalme_verification_ref,
        x_actor_user_id,
        x_digitalme_assertion,
    )
    case_id = _normalize_uuid(case_id, "case_id")
    request_hash = _payload_hash(payload.model_dump())

    with get_conn() as conn:
        with conn.cursor() as cur:
            case = _load_case(cur, case_id, principal, actor_user_id, for_update=True)
            _lock_idempotency_key(
                cur, str(case["workspace_id"]), "participant-approval", x_idempotency_key
            )
            if _check_idempotency(
                cur,
                workspace_id=str(case["workspace_id"]),
                case_id=case_id,
                scope="participant-approval",
                idempotency_key=x_idempotency_key,
                request_hash=request_hash,
            ):
                return {
                    "case": case,
                    "next_gate": (
                        "VIRTUAL_ESTATE_LICENSE"
                        if case["state"] == "HOLD_FOR_ESTATE_LICENSE"
                        else "SYNNERGYZE_PLAN_REVISION"
                    ),
                    "protected_execution_authorized": False,
                }

            _require_state(case, {"PLAN_READY", "HOLD_FOR_ESTATE_LICENSE"})
            target_state = "HOLD_FOR_ESTATE_LICENSE" if payload.accepted else "PLAN_READY"
            previous = {"state": case["state"]}

            cur.execute(
                """
                UPDATE gmt.onboarding_cases
                   SET state = %s,
                       updated_at = NOW()
                 WHERE id = %s
                 RETURNING *
                """,
                (target_state, case_id),
            )
            updated = cur.fetchone()

            _record_idempotency(
                cur,
                workspace_id=str(updated["workspace_id"]),
                case_id=case_id,
                scope="participant-approval",
                idempotency_key=x_idempotency_key,
                request_hash=request_hash,
                resulting_state=target_state,
            )
            _emit_river_event(
                cur,
                workspace_id=str(updated["workspace_id"]),
                actor_user_id=actor_user_id,
                principal=principal,
                object_id=case_id,
                action="participant_plan_decision",
                event_type=(
                    "GMT_PARTICIPANT_PLAN_APPROVED"
                    if payload.accepted
                    else "GMT_PARTICIPANT_PLAN_DECLINED"
                ),
                idempotency_key=f"{x_idempotency_key}:participant-decision",
                previous_state=previous,
                new_state={"state": target_state},
                verification_ref=verification_ref,
                consent_context={"participant_accepted_plan": payload.accepted},
            )
        conn.commit()

    return {
        "case": updated,
        "next_gate": (
            "VIRTUAL_ESTATE_LICENSE"
            if payload.accepted
            else "SYNNERGYZE_PLAN_REVISION"
        ),
        "protected_execution_authorized": False,
    }


@router.get("/onboarding-cases/{case_id}")
def get_onboarding_case(
    case_id: str,
    x_digitalme_principal: str | None = Header(None, alias="X-DigitalMe-Principal"),
    x_digitalme_verification_ref: str | None = Header(
        None, alias="X-DigitalMe-Verification-Ref"
    ),
    x_actor_user_id: str | None = Header(None, alias="X-Actor-User-Id"),
    x_digitalme_assertion: str | None = Header(None, alias="X-DigitalMe-Assertion"),
):
    principal, _, actor_user_id = _require_trusted_context(
        x_digitalme_principal,
        x_digitalme_verification_ref,
        x_actor_user_id,
        x_digitalme_assertion,
    )
    case_id = _normalize_uuid(case_id, "case_id")
    with get_conn() as conn:
        with conn.cursor() as cur:
            return _load_case(cur, case_id, principal, actor_user_id)
