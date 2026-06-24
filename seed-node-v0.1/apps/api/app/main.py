from fastapi import FastAPI
from pydantic import BaseModel
import json
from app.db import get_conn

app = FastAPI(title="Synnergyze Seed Node API", version="0.1.0")

@app.get("/health")
def health():
    return {"status": "ok", "system": "synnergyze-seed-node", "version": "0.1.0"}

class WorkspaceCreate(BaseModel):
    owner_display_name: str
    owner_email: str | None = None
    name: str
    workspace_type: str = "textile"
    upi_id: str | None = None

@app.post("/workspaces")
def create_workspace(payload: WorkspaceCreate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO platform.users (display_name, email) VALUES (%s, %s) RETURNING id", (payload.owner_display_name, payload.owner_email))
            user_id = cur.fetchone()["id"]
            cur.execute(
                "INSERT INTO workspace.workspaces (owner_user_id, name, workspace_type, upi_id, pricing_enabled) VALUES (%s,%s,%s,%s,%s) RETURNING *",
                (user_id, payload.name, payload.workspace_type, payload.upi_id, bool(payload.upi_id))
            )
            ws = cur.fetchone()
            cur.execute("INSERT INTO workspace.members (workspace_id, user_id, role, status) VALUES (%s,%s,'owner','active')", (ws["id"], user_id))
            cur.execute("INSERT INTO riveros.evidence_events (workspace_id, actor_user_id, event_type, object_type, object_id, evidence_json) VALUES (%s,%s,'WORKSPACE_CREATED','workspace',%s,%s::jsonb)", (ws["id"], user_id, ws["id"], '{"module":"workspace"}'))
        conn.commit()
    return {"workspace": ws, "owner_user_id": user_id}

class MaterialPassportCreate(BaseModel):
    workspace_id: str
    material_name: str
    colour_code: str | None = None
    shade_family: str | None = None
    fabric_type: str | None = None
    composition: str | None = None
    gsm: float | None = None
    supplier: str | None = None
    evidence_image_url: str | None = None

@app.post("/textile/material-passports")
def create_material_passport(payload: MaterialPassportCreate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO textile.material_passports (workspace_id, material_name, colour_code, shade_family, fabric_type, composition, gsm, supplier, evidence_image_url) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING *",
                (payload.workspace_id, payload.material_name, payload.colour_code, payload.shade_family, payload.fabric_type, payload.composition, payload.gsm, payload.supplier, payload.evidence_image_url)
            )
            mp = cur.fetchone()
            cur.execute("INSERT INTO riveros.evidence_events (workspace_id, event_type, object_type, object_id, evidence_json) VALUES (%s,'MATERIAL_PASSPORT_CREATED','material_passport',%s,%s::jsonb)", (payload.workspace_id, mp["id"], '{"module":"textile"}'))
        conn.commit()
    return mp

class DesignProjectCreate(BaseModel):
    workspace_id: str
    name: str
    garment_type: str

@app.post("/textile/design-projects")
def create_design_project(payload: DesignProjectCreate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO textile.design_projects (workspace_id, name, garment_type) VALUES (%s,%s,%s) RETURNING *", (payload.workspace_id, payload.name, payload.garment_type))
            project = cur.fetchone()
        conn.commit()
    return project

class BOMCreate(BaseModel):
    design_project_id: str
    bom_json: dict

@app.post("/textile/bom")
def create_bom(payload: BOMCreate):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO textile.bom_versions (design_project_id, bom_json) VALUES (%s,%s::jsonb) RETURNING *", (payload.design_project_id, json.dumps(payload.bom_json)))
            bom = cur.fetchone()
        conn.commit()
    return bom

class PaymentEventCreate(BaseModel):
    workspace_id: str
    service_code: str
    gross_amount_paise: int
    platform_fee_paise: int = 0
    external_reference: str | None = None

@app.post("/silk/payment-events")
def create_payment_event(payload: PaymentEventCreate):
    owner_receivable = payload.gross_amount_paise - payload.platform_fee_paise
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO silk.payment_events (workspace_id, service_code, gross_amount_paise, platform_fee_paise, owner_receivable_paise, external_reference) VALUES (%s,%s,%s,%s,%s,%s) RETURNING *",
                (payload.workspace_id, payload.service_code, payload.gross_amount_paise, payload.platform_fee_paise, owner_receivable, payload.external_reference)
            )
            payment = cur.fetchone()
            cur.execute("INSERT INTO riveros.evidence_events (workspace_id, event_type, object_type, object_id, evidence_json) VALUES (%s,'PAYMENT_EVENT_RECORDED','payment_event',%s,%s::jsonb)", (payload.workspace_id, payment["id"], '{"module":"silk"}'))
        conn.commit()
    return payment

class BusinessConvert(BaseModel):
    workspace_id: str
    legal_name: str
    trade_name: str | None = None
    gstin: str | None = None
    invoice_prefix: str | None = None

@app.post("/business/convert-workspace")
def convert_workspace(payload: BusinessConvert):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO business.business_profiles (workspace_id, legal_name, trade_name, gstin, invoice_prefix, status) VALUES (%s,%s,%s,%s,%s,'active') RETURNING *", (payload.workspace_id, payload.legal_name, payload.trade_name, payload.gstin, payload.invoice_prefix))
            business = cur.fetchone()
            cur.execute("INSERT INTO genesis.registered_units (business_profile_id, unit_name, unit_type) VALUES (%s,%s,'business') RETURNING *", (business["id"], payload.trade_name or payload.legal_name))
            unit = cur.fetchone()
            cur.execute("INSERT INTO riveros.evidence_events (workspace_id, event_type, object_type, object_id, evidence_json) VALUES (%s,'WORKSPACE_CONVERTED_TO_BUSINESS','business_profile',%s,%s::jsonb)", (payload.workspace_id, business["id"], '{"module":"genesis"}'))
        conn.commit()
    return {"business_profile": business, "genesis_unit": unit}

@app.get("/riveros/events/{workspace_id}")
def list_evidence_events(workspace_id: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM riveros.evidence_events WHERE workspace_id = %s ORDER BY created_at DESC LIMIT 100", (workspace_id,))
            return {"events": cur.fetchall()}
