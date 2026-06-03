from __future__ import annotations

import hashlib
import inspect
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Iterable

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text

router = APIRouter(prefix="/api", tags=["Auditoria Forense"])


LEDGER_SQL = """
SELECT
    ji.id,
    ji.date,
    ji.account_code,
    COALESCE(ji.account_name, ac.name, ji.account_code) AS account_name,
    ji.voucher_number,
    ji.description,
    ji.debit,
    ji.credit,
    ji.taxpayer_ruc,
    COALESCE(ji.counterparty_name, xd.issuer_name, xd.receiver_name, '') AS counterparty_name,
    ji.hash_payload,
    ji.row_hash,
    ji.previous_hash,
    ji.xml_document_id,
    xd.raw_xml,
    COALESCE(xd.parsed_payload, '{}'::jsonb) AS xml_payload,
    COALESCE(tv.status, 'PENDIENTE') AS taxpayer_status
FROM journal_items ji
LEFT JOIN accounts ac
    ON ac.tenant_id = ji.tenant_id
   AND ac.code = ji.account_code
LEFT JOIN xml_documents xd
    ON xd.tenant_id = ji.tenant_id
   AND xd.id = ji.xml_document_id
LEFT JOIN taxpayer_validations tv
    ON tv.tenant_id = ji.tenant_id
   AND tv.ruc = ji.taxpayer_ruc
WHERE ji.account_code = :account_code
  AND ji.tenant_id = :tenant_id
ORDER BY ji.date ASC, ji.voucher_number ASC, ji.id ASC
"""


def _resolve_tenant_id(request: Request, query_tenant_id: str | None, header_tenant_id: str | None) -> str:
    tenant_id = str(
        getattr(request.state, "tenant_id", None)
        or header_tenant_id
        or query_tenant_id
        or ""
    ).strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="Tenant activo requerido")
    return tenant_id


def _to_decimal(value: Any) -> Decimal:
    if value in (None, ""):
        return Decimal("0.00")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0.00")


def _to_float(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _format_date(value: Any) -> str:
    if not value:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%d-%m-%Y")
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).strftime("%d-%m-%Y")
    except ValueError:
        return text[:10]


def _as_dict(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    if hasattr(row, "_mapping"):
        return dict(row._mapping)
    if hasattr(row, "items"):
        return dict(row.items())
    return dict(row)


def _normalise_database_url(database_url: str) -> str:
    if database_url.startswith("postgres://"):
        return database_url.replace("postgres://", "postgresql://", 1)
    return database_url


def _redact_database_url(database_url: str) -> str:
    return re.sub(r"://([^:/@]+):([^@]+)@", r"://\1:***@", database_url)


def _normalise_xml_payload(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {"items": parsed}
        except json.JSONDecodeError:
            return {"raw": value}
    return {"raw": value}


def _extract_xml_summary(row: dict[str, Any]) -> dict[str, Any]:
    payload = _normalise_xml_payload(row.get("xml_payload"))
    issuer = payload.get("emisor") or payload.get("issuer") or {}
    receiver = payload.get("receptor") or payload.get("receiver") or {}
    items = payload.get("items") or payload.get("detalles") or payload.get("lines") or []

    return {
        "document_id": row.get("xml_document_id"),
        "emisor": issuer,
        "receptor": receiver,
        "items": items if isinstance(items, list) else [items],
        "raw_xml": row.get("raw_xml") or payload.get("raw") or "",
    }


def _canonical_hash_payload(row: dict[str, Any], debit: Decimal, credit: Decimal, previous_hash: str) -> str:
    stored_payload = row.get("hash_payload")
    if stored_payload:
        if isinstance(stored_payload, (dict, list)):
            encoded = json.dumps(stored_payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        else:
            encoded = str(stored_payload).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    payload = {
        "id": row.get("id"),
        "date": _json_default(row.get("date")),
        "account_code": row.get("account_code"),
        "voucher_number": row.get("voucher_number"),
        "description": row.get("description") or "",
        "debit": str(debit),
        "credit": str(credit),
        "taxpayer_ruc": row.get("taxpayer_ruc") or "",
        "previous_hash": previous_hash or "",
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _build_recommendations(movements: Iterable[dict[str, Any]]) -> list[str]:
    rows = list(movements)
    if not rows:
        return ["Sin movimientos para analizar en la cuenta seleccionada."]

    recommendations: list[str] = []
    total_abs = sum(abs(_to_decimal(row.get("debit"))) + abs(_to_decimal(row.get("credit"))) for row in rows)
    voucher_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    ruc_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0.00"))
    status_counter: Counter[str] = Counter()
    invalid_hash_count = 0

    for row in rows:
        amount = abs(_to_decimal(row.get("debit"))) + abs(_to_decimal(row.get("credit")))
        voucher = str(row.get("voucher_number") or "SIN VOUCHER")
        ruc = str(row.get("taxpayer_ruc") or "SIN RUC")
        voucher_totals[voucher] += amount
        ruc_totals[ruc] += amount
        status_counter[str(row.get("taxpayer_status") or "PENDIENTE").upper()] += 1
        if row.get("_hash_valid") is False:
            invalid_hash_count += 1

    top_voucher, top_voucher_amount = max(voucher_totals.items(), key=lambda item: item[1])
    top_ruc, top_ruc_amount = max(ruc_totals.items(), key=lambda item: item[1])
    concentration = (top_ruc_amount / total_abs * Decimal("100")) if total_abs else Decimal("0.00")
    average = total_abs / Decimal(max(len(rows), 1))

    if concentration >= Decimal("40.00") and top_ruc != "SIN RUC":
        recommendations.append(
            f"Deteccion de concentracion: el RUC {top_ruc} acumula {concentration:.1f}% del movimiento de la cuenta."
        )
    if top_voucher_amount > average * Decimal("2.5"):
        recommendations.append(
            f"Riesgo detectado en voucher {top_voucher}: importe superior a 2.5x del promedio historico del periodo."
        )
    if status_counter.get("NO HABIDO", 0) or status_counter.get("BAJA", 0):
        recommendations.append(
            "Validacion RUC: existen contribuyentes con estado critico. Revisar sustento tributario antes del cierre."
        )
    if invalid_hash_count:
        recommendations.append(
            f"Inmutabilidad comprometida: {invalid_hash_count} movimiento(s) no validan contra la cadena SHA-256."
        )
    if not recommendations:
        recommendations.append("No se detectaron anomalias materiales; mantener monitoreo de vouchers y RUCs con mayor rotacion.")
    return recommendations


async def _maybe_call_ruc_validator(request: Request, ruc: str, current_status: str, tenant_id: str) -> str:
    if not ruc or current_status not in {"", "PENDIENTE", "UNKNOWN"}:
        return current_status or "PENDIENTE"

    validator = getattr(request.app.state, "ruc_validator", None)
    if validator is None:
        return "PENDIENTE"

    if not callable(validator):
        return "PENDIENTE"

    try:
        result = validator(ruc, tenant_id=tenant_id)
    except TypeError:
        result = validator(ruc)

    if inspect.isawaitable(result):
        result = await result
    if isinstance(result, dict):
        return str(result.get("status") or result.get("estado") or current_status or "PENDIENTE").upper()
    if result:
        return str(result).upper()
    return "PENDIENTE"


def _fetch_rows_from_postgres(request: Request, account_code: str, tenant_id: str) -> list[dict[str, Any]]:
    engine = getattr(request.app.state, "pg_engine", None)
    if engine is None:
        raise HTTPException(
            status_code=503,
            detail="PostgreSQL engine no configurado. Inicializa request.app.state.pg_engine con SQLAlchemy create_engine().",
        )

    with engine.begin() as conn:
        conn.execute(text("SELECT set_config('app.tenant_id', :tenant_id, true)"), {"tenant_id": tenant_id})
        rows = conn.execute(
            text(LEDGER_SQL),
            {"account_code": account_code, "tenant_id": tenant_id},
        ).fetchall()
        return [_as_dict(row) for row in rows]


def init_audit_pg_engine(app: Any, database_url: str, **engine_options: Any) -> None:
    from sqlalchemy import create_engine

    normalised_url = _normalise_database_url(database_url)
    app.state.pg_engine = create_engine(normalised_url, pool_pre_ping=True, **engine_options)
    app.state.pg_database_url = _redact_database_url(normalised_url)


def close_audit_pg_engine(app: Any) -> None:
    engine = getattr(app.state, "pg_engine", None)
    if engine is not None:
        engine.dispose()


@router.get("/ledger/analytic/{account_code}")
async def get_analytic_ledger(
    account_code: str,
    request: Request,
    tenant_id: str | None = Query(default=None, description="Fallback local; preferir X-Tenant-Id o request.state.tenant_id."),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-Id"),
):
    """Libro Mayor Analitico con RLS, hash encadenado, XML y validacion RUC."""
    active_tenant_id = _resolve_tenant_id(request, tenant_id, x_tenant_id)
    rows = await run_in_threadpool(_fetch_rows_from_postgres, request, account_code, active_tenant_id)

    running_balance = Decimal("0.00")
    previous_expected_hash = ""
    movements: list[dict[str, Any]] = []
    account_name = account_code

    for index, row in enumerate(rows):
        debit = _to_decimal(row.get("debit"))
        credit = _to_decimal(row.get("credit"))
        running_balance += debit - credit

        stored_previous_hash = str(row.get("previous_hash") or "")
        stored_hash = str(row.get("row_hash") or "")
        expected_hash = _canonical_hash_payload(row, debit, credit, stored_previous_hash or previous_expected_hash)
        chained = index == 0 or stored_previous_hash == previous_expected_hash
        hash_valid = bool(stored_hash) and stored_hash == expected_hash and chained
        previous_expected_hash = stored_hash or expected_hash
        row["_hash_valid"] = hash_valid

        taxpayer_status = await _maybe_call_ruc_validator(
            request,
            str(row.get("taxpayer_ruc") or ""),
            str(row.get("taxpayer_status") or "PENDIENTE").upper(),
            active_tenant_id,
        )
        account_name = str(row.get("account_name") or account_name)

        movements.append(
            {
                "id": str(row.get("id") or ""),
                "date": _format_date(row.get("date")),
                "voucher": row.get("voucher_number") or "",
                "glosa": row.get("description") or "",
                "debit": _to_float(debit),
                "credit": _to_float(credit),
                "balance": _to_float(running_balance),
                "ruc": row.get("taxpayer_ruc") or "",
                "counterparty_name": row.get("counterparty_name") or "",
                "taxpayer_status": taxpayer_status,
                "hash": stored_hash or expected_hash,
                "previous_hash": stored_previous_hash,
                "hash_valid": hash_valid,
                "hash_chain_valid": chained,
                "xml": _extract_xml_summary(row),
            }
        )

    return {
        "ok": True,
        "tenant_id": active_tenant_id,
        "account_id": account_code,
        "account_code": account_code,
        "code": account_code,
        "name": account_name,
        "period": datetime.utcnow().strftime("%Y-%m"),
        "current_balance": _to_float(running_balance),
        "movements": movements,
        "recommendations": _build_recommendations(rows),
        "rls": {
            "enabled": True,
            "session_setting": "app.tenant_id",
            "tenant_source": "request.state.tenant_id | X-Tenant-Id | tenant_id query fallback",
        },
    }
