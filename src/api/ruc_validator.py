from __future__ import annotations

from typing import Any

from sqlalchemy import text


def validate_ruc_from_master(engine: Any, tenant_id: str, ruc: str) -> dict[str, str]:
    if not ruc:
        return {"ruc": "", "status": "PENDIENTE"}

    with engine.begin() as conn:
        conn.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})
        row = conn.execute(
            text(
                """
                SELECT ruc, status, legal_name
                FROM taxpayer_validations
                WHERE tenant_id = :tenant_id
                  AND ruc = :ruc
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id, "ruc": ruc},
        ).fetchone()

    if not row:
        return {"ruc": ruc, "status": "PENDIENTE"}

    data = dict(row._mapping)
    return {
        "ruc": str(data["ruc"]),
        "status": str(data["status"] or "PENDIENTE").upper(),
        "legal_name": str(data["legal_name"] or ""),
    }
