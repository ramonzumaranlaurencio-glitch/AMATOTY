"""
Trujillo SafePay PRO - Microservicio independiente
Puerto  : 5001  (local) | variable en producción (Render)
DB      : PostgreSQL (producción) / SQLite (desarrollo local)
Config  : variables de entorno (.env o Render dashboard)
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

# Asegura que db.py se encuentre sin importar desde dónde se ejecuta
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from flask import Flask, abort, jsonify, redirect, render_template, request, url_for
from flask_cors import CORS
from sqlalchemy import text

from db import DB_BACKEND, engine, init_db, migrate_db, row_to_dict

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(name)s  %(message)s")
logger = logging.getLogger("safepay")

# ─── Variables de entorno ─────────────────────────────────────────────────────
SECRET_KEY          = os.getenv("SECRET_KEY",          "safepay-dev-secret-2026")
PAYMENT_PROVIDER    = os.getenv("PAYMENT_PROVIDER",    "manual")   # stripe | manual
PAYMENT_SECRET_KEY  = os.getenv("PAYMENT_SECRET_KEY",  "")
PAYMENT_PUBLIC_KEY  = os.getenv("PAYMENT_PUBLIC_KEY",  "")
WEBHOOK_SECRET      = os.getenv("WEBHOOK_SECRET",      "")
SAFEPAY_PORT        = int(os.getenv("PORT",            "5001"))

# BASE_URL: en Render se inyecta RENDER_EXTERNAL_URL automáticamente.
# En local usamos http://127.0.0.1:5001
BASE_URL = (
    os.getenv("BASE_URL")
    or os.getenv("RENDER_EXTERNAL_URL")
    or f"http://127.0.0.1:{SAFEPAY_PORT}"
)
# Render a veces entrega la URL sin esquema — lo normalizamos
if BASE_URL and not BASE_URL.startswith("http"):
    BASE_URL = "https://" + BASE_URL
BASE_URL = BASE_URL.rstrip("/")

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5050,http://localhost:5050")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

# ─── App Flask ────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = SECRET_KEY

CORS(app,
     resources={r"/api/*": {"origins": "*"}},
     allow_headers=["Content-Type", "Authorization", "Accept"],
     methods=["GET", "POST", "PUT", "OPTIONS"],
     supports_credentials=False)

# ─── Catálogos ────────────────────────────────────────────────────────────────
PAYMENT_METHODS  = ["Yape", "Plin", "BCP", "Interbank", "Efectivo", "Tarjeta", "Online"]
CURRENCIES       = ["PEN", "USD"]
PAYMENT_STATUSES = ["pendiente", "procesando", "pagado", "completado", "rechazado", "reembolsado"]

# ─── Init BD ──────────────────────────────────────────────────────────────────
init_db()
migrate_db()

# ─── Helpers ──────────────────────────────────────────────────────────────────
def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _new_sp_id() -> str:
    return "SP-" + uuid.uuid4().hex[:10].upper()


def _log_transaction(conn, sp_id: str, action: str, notes: str = "") -> None:
    conn.execute(
        text("INSERT INTO transactions (id, payment_id, action, notes, created_at) "
             "VALUES (:id, :spid, :action, :notes, :n)"),
        {"id": uuid.uuid4().hex, "spid": sp_id, "action": action, "notes": notes, "n": now_iso()},
    )


# ─── Proveedor de pagos ───────────────────────────────────────────────────────
def _get_stripe():
    """Retorna el módulo stripe configurado, o None si no está disponible."""
    if not PAYMENT_SECRET_KEY:
        return None
    try:
        import stripe
        stripe.api_key = PAYMENT_SECRET_KEY
        return stripe
    except ImportError:
        logger.warning("Stripe no instalado. Ejecuta: pip install stripe")
        return None


def _create_stripe_checkout(sp_id: str, amount: float, currency: str,
                             description: str, customer_email: str) -> dict:
    """
    Crea una Stripe Checkout Session.
    Retorna: {"payment_id": session_id, "checkout_url": url}
    """
    stripe = _get_stripe()
    if not stripe:
        raise RuntimeError(
            "Stripe no configurado. Verifica PAYMENT_SECRET_KEY y que stripe esté instalado."
        )

    amount_cents = int(round(amount * 100))
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": currency.lower(),
                "unit_amount": amount_cents,
                "product_data": {"name": description or f"Pago SafePay {sp_id}"},
            },
            "quantity": 1,
        }],
        mode="payment",
        customer_email=customer_email or None,
        metadata={"sp_id": sp_id},
        success_url=f"{BASE_URL}/payment/{sp_id}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{BASE_URL}/payment/{sp_id}/cancel",
    )
    return {"payment_id": session.id, "checkout_url": session.url}


def _handle_payment_completed(provider_payment_id: str, transaction_id: str) -> None:
    """Marca el pago como PAGADO basado en el ID del proveedor. Idempotente."""
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id, status FROM payments WHERE payment_id = :pid"),
            {"pid": provider_payment_id},
        ).fetchone()

        if not row:
            logger.warning("Webhook: pago no encontrado para provider ID %s", provider_payment_id)
            return
        if row_to_dict(row).get("status") == "pagado":
            return  # Ya procesado — idempotencia

        n = now_iso()
        conn.execute(
            text("UPDATE payments SET status='pagado', transaction_id=:tid, updated_at=:n "
                 "WHERE payment_id=:pid"),
            {"tid": transaction_id, "pid": provider_payment_id, "n": n},
        )
        sp_id = row_to_dict(row)["id"]
        _log_transaction(conn, sp_id, "pagado",
                         f"Confirmado por proveedor. Transaction: {transaction_id}")
        logger.info("Pago %s marcado como PAGADO (tx: %s)", sp_id, transaction_id)


# ═══════════════════════════════════════════════════════════════════════════════
#  VISTAS WEB  (UI independiente en http://127.0.0.1:5001)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
def dashboard():
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM payments ORDER BY created_at DESC LIMIT 50")
        ).fetchall()
        stats_row = conn.execute(text("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(CASE WHEN status IN ('completado','pagado') THEN amount END), 0) AS total_amount,
                COALESCE(SUM(CASE WHEN status IN ('completado','pagado') AND currency='PEN' THEN amount END), 0) AS total_pen,
                COALESCE(SUM(CASE WHEN status IN ('completado','pagado') AND currency='USD' THEN amount END), 0) AS total_usd,
                SUM(CASE WHEN status='pendiente'   THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status IN ('completado','pagado') THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status='rechazado'   THEN 1 ELSE 0 END) AS rejected
            FROM payments
        """)).fetchone()

    stats = row_to_dict(stats_row) if stats_row else {}
    stats.pop("metadata", None)
    payments_list = [row_to_dict(r) for r in rows]
    return render_template(
        "dashboard.html",
        payments=payments_list,
        stats=stats,
        methods=PAYMENT_METHODS,
    )


@app.route("/payment/new", methods=["GET", "POST"])
def payment_new():
    if request.method == "POST":
        pay_id       = _new_sp_id()
        amount       = float(request.form.get("amount", 0))
        currency     = request.form.get("currency", "PEN")
        method       = request.form.get("method", "Yape")
        description  = request.form.get("description", "")
        customer     = request.form.get("customer", "")
        customer_email = request.form.get("customer_email", "")
        metadata     = json.dumps({"source": "web-form"})

        with engine.begin() as conn:
            n = now_iso()
            conn.execute(text(
                "INSERT INTO payments "
                "(id, amount, currency, method, description, customer, customer_email, "
                " status, provider, metadata, created_at, updated_at) "
                "VALUES (:id,:amount,:currency,:method,:desc,:customer,:email,"
                "        'pendiente','manual',:meta,:n,:n)"
            ), {"id": pay_id, "amount": amount, "currency": currency, "method": method,
                "desc": description, "customer": customer, "email": customer_email,
                "meta": metadata, "n": n})
            _log_transaction(conn, pay_id, "creado", "Pago creado vía formulario web")
        return redirect(url_for("payment_detail", pay_id=pay_id))

    return render_template(
        "payment_form.html",
        methods=PAYMENT_METHODS,
        currencies=CURRENCIES,
    )


@app.route("/payment/<pay_id>")
def payment_detail(pay_id):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM payments WHERE id = :id"), {"id": pay_id}
        ).fetchone()
        if not row:
            return render_template("404.html"), 404
        history = conn.execute(
            text("SELECT * FROM transactions WHERE payment_id = :id ORDER BY created_at DESC"),
            {"id": pay_id},
        ).fetchall()

    return render_template(
        "payment_detail.html",
        payment=row_to_dict(row),
        history=[row_to_dict(h) for h in history],
        statuses=PAYMENT_STATUSES,
        payment_provider=PAYMENT_PROVIDER,
        payment_public_key=PAYMENT_PUBLIC_KEY,
    )


@app.route("/payment/<pay_id>/update", methods=["POST"])
def payment_update(pay_id):
    new_status = request.form.get("status")
    notes      = request.form.get("notes", "")

    if new_status not in PAYMENT_STATUSES:
        return "Estado inválido", 400

    with engine.begin() as conn:
        conn.execute(
            text("UPDATE payments SET status=:s, updated_at=:n WHERE id=:id"),
            {"s": new_status, "n": now_iso(), "id": pay_id},
        )
        _log_transaction(conn, pay_id, new_status, notes)
    return redirect(url_for("payment_detail", pay_id=pay_id))


# ── Checkout online ────────────────────────────────────────────────────────────

@app.route("/payment/<pay_id>/checkout", methods=["POST"])
def payment_checkout(pay_id):
    """Inicia el pago online con el proveedor configurado."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM payments WHERE id = :id"), {"id": pay_id}
        ).fetchone()
    if not row:
        abort(404)

    payment = row_to_dict(row)

    if payment["status"] not in ("pendiente", "procesando"):
        return redirect(url_for("payment_detail", pay_id=pay_id))

    if PAYMENT_PROVIDER == "stripe":
        try:
            result = _create_stripe_checkout(
                sp_id=pay_id,
                amount=payment["amount"],
                currency=payment["currency"],
                description=payment.get("description") or f"Pago {pay_id}",
                customer_email=payment.get("customer_email") or "",
            )
            with engine.begin() as conn:
                n = now_iso()
                conn.execute(text(
                    "UPDATE payments SET payment_id=:pid, checkout_url=:url, "
                    "provider='stripe', status='procesando', updated_at=:n WHERE id=:id"
                ), {"pid": result["payment_id"], "url": result["checkout_url"],
                    "n": n, "id": pay_id})
                _log_transaction(conn, pay_id, "checkout_iniciado",
                                 f"Stripe session: {result['payment_id']}")
            return redirect(result["checkout_url"])
        except Exception as exc:
            logger.error("Checkout error: %s", exc)
            return render_template("checkout_error.html", error=str(exc),
                                   pay_id=pay_id), 500
    else:
        # Proveedor manual: mostrar detalle con instrucciones
        return redirect(url_for("payment_detail", pay_id=pay_id))


@app.route("/payment/<pay_id>/success")
def payment_success(pay_id):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM payments WHERE id = :id"), {"id": pay_id}
        ).fetchone()
    return render_template("pay_success.html", payment=row_to_dict(row) if row else {})


@app.route("/payment/<pay_id>/cancel")
def payment_cancel(pay_id):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM payments WHERE id = :id"), {"id": pay_id}
        ).fetchone()
    return render_template("pay_cancel.html", payment=row_to_dict(row) if row else {})


# ═══════════════════════════════════════════════════════════════════════════════
#  API REST  (llamada desde LCA PRO y clientes externos)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/health")
def health():
    return jsonify({
        "status":   "ok",
        "service":  "SafePay PRO",
        "port":     SAFEPAY_PORT,
        "provider": PAYMENT_PROVIDER,
        "db":       DB_BACKEND,
    })


# ── Listar pagos ──────────────────────────────────────────────────────────────
@app.route("/api/payments", methods=["GET"])
def api_list_payments():
    status_filter = request.args.get("status")
    with engine.connect() as conn:
        if status_filter:
            rows = conn.execute(
                text("SELECT * FROM payments WHERE status=:s ORDER BY created_at DESC"),
                {"s": status_filter},
            ).fetchall()
        else:
            rows = conn.execute(
                text("SELECT * FROM payments ORDER BY created_at DESC")
            ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])


# ── Crear pago (v2 — con integración de proveedor) ───────────────────────────
@app.route("/api/payments/create", methods=["POST"])
def api_payments_create():
    """
    Endpoint principal de producción.
    Body JSON:
    {
        "amount": 150.00,
        "currency": "PEN",
        "method": "Online",
        "description": "Pago de producto",
        "customer": "Juan Pérez",
        "customer_email": "juan@email.com",
        "metadata": {}
    }
    Respuesta incluye checkout_url cuando PAYMENT_PROVIDER=stripe.
    """
    data = request.get_json(force=True, silent=True) or {}

    amount = float(data.get("amount", 0))
    if amount <= 0:
        return jsonify({"error": "amount debe ser mayor a 0"}), 400

    method   = data.get("method", "Online")
    currency = data.get("currency", "PEN")
    pay_id   = _new_sp_id()
    n        = now_iso()

    with engine.begin() as conn:
        conn.execute(text(
            "INSERT INTO payments "
            "(id, amount, currency, method, description, customer, customer_email, "
            " status, provider, metadata, created_at, updated_at) "
            "VALUES (:id,:amount,:currency,:method,:desc,:customer,:email,"
            "        'pendiente',:prov,:meta,:n,:n)"
        ), {
            "id": pay_id, "amount": amount, "currency": currency, "method": method,
            "desc":     data.get("description", ""),
            "customer": data.get("customer", ""),
            "email":    data.get("customer_email", ""),
            "prov":     PAYMENT_PROVIDER,
            "meta":     json.dumps(data.get("metadata") or {}),
            "n": n,
        })
        _log_transaction(conn, pay_id, "creado", "Creado vía API v2")

    response = {
        "id":            pay_id,
        "status":        "pendiente",
        "amount":        amount,
        "currency":      currency,
        "method":        method,
        "provider":      PAYMENT_PROVIDER,
        "dashboard_url": f"{BASE_URL}/payment/{pay_id}",
    }

    # Si el proveedor es Stripe, crear checkout session de inmediato
    if PAYMENT_PROVIDER == "stripe":
        try:
            result = _create_stripe_checkout(
                sp_id=pay_id,
                amount=amount,
                currency=currency,
                description=data.get("description") or f"Pago {pay_id}",
                customer_email=data.get("customer_email") or "",
            )
            with engine.begin() as conn:
                conn.execute(text(
                    "UPDATE payments SET payment_id=:pid, checkout_url=:url, "
                    "provider='stripe', status='procesando', updated_at=:n WHERE id=:id"
                ), {"pid": result["payment_id"], "url": result["checkout_url"],
                    "n": now_iso(), "id": pay_id})
                _log_transaction(conn, pay_id, "checkout_iniciado",
                                 f"Stripe session: {result['payment_id']}")
            response.update({
                "status":       "procesando",
                "payment_id":   result["payment_id"],
                "checkout_url": result["checkout_url"],
            })
        except Exception as exc:
            logger.error("Stripe checkout error: %s", exc)
            response["stripe_error"] = str(exc)

    return jsonify(response), 201


# ── Crear pago (v1 — compatibilidad con safepay_client.py) ───────────────────
@app.route("/api/payment/create", methods=["POST"])
def api_create_payment():
    """Compatibilidad hacia atrás con safepay_client.py."""
    return api_payments_create()


# ── Obtener pago ──────────────────────────────────────────────────────────────
@app.route("/api/payment/<pay_id>", methods=["GET"])
def api_get_payment(pay_id):
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT * FROM payments WHERE id=:id"), {"id": pay_id}
        ).fetchone()
    if not row:
        return jsonify({"error": "Pago no encontrado"}), 404
    return jsonify(row_to_dict(row))


# ── Cambiar estado (v1 — compatibilidad) ─────────────────────────────────────
@app.route("/api/payment/<pay_id>/process", methods=["POST"])
def api_process_payment(pay_id):
    data       = request.get_json(force=True, silent=True) or {}
    new_status = data.get("status", "procesando")
    notes      = data.get("notes", "")

    if new_status not in PAYMENT_STATUSES:
        return jsonify({"error": f"status inválido. Opciones: {PAYMENT_STATUSES}"}), 400

    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT id FROM payments WHERE id=:id"), {"id": pay_id}
        ).fetchone()
        if not row:
            return jsonify({"error": "Pago no encontrado"}), 404

        n = now_iso()
        conn.execute(
            text("UPDATE payments SET status=:s, updated_at=:n WHERE id=:id"),
            {"s": new_status, "n": n, "id": pay_id},
        )
        _log_transaction(conn, pay_id, new_status, notes)

    return jsonify({"id": pay_id, "status": new_status, "updated_at": n})


# ── Estadísticas ──────────────────────────────────────────────────────────────
@app.route("/api/stats", methods=["GET"])
def api_stats():
    with engine.connect() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(CASE WHEN status IN ('completado','pagado') THEN amount END), 0) AS total_amount,
                SUM(CASE WHEN status='pendiente'                  THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status IN ('completado','pagado')   THEN 1 ELSE 0 END) AS completed,
                SUM(CASE WHEN status='rechazado'                  THEN 1 ELSE 0 END) AS rejected
            FROM payments
        """)).fetchone()
    d = row_to_dict(row) if row else {}
    d.pop("metadata", None)
    return jsonify(d)


# ═══════════════════════════════════════════════════════════════════════════════
#  WEBHOOK  (Stripe → SafePay)
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/api/payments/webhook", methods=["POST"])
def api_webhook():
    """
    Endpoint de webhook para Stripe.
    Verifica la firma HMAC antes de procesar cualquier evento.
    Configura en Stripe Dashboard → Webhooks → Endpoint URL:
        https://tu-safepay.onrender.com/api/payments/webhook
    Eventos a escuchar: checkout.session.completed
    """
    payload    = request.get_data()   # bytes crudos — necesario para verificar firma
    sig_header = request.headers.get("Stripe-Signature", "")

    if not WEBHOOK_SECRET:
        logger.warning("WEBHOOK_SECRET no configurado")
        return jsonify({"error": "Webhook no configurado en este servidor"}), 503

    stripe = _get_stripe()
    if not stripe:
        return jsonify({"error": "Stripe no disponible"}), 503

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        logger.warning("Webhook: firma inválida")
        return jsonify({"error": "Firma inválida"}), 400
    except Exception as exc:
        logger.error("Webhook parse error: %s", exc)
        return jsonify({"error": "Error procesando webhook"}), 400

    event_type = event.get("type", "")
    logger.info("Webhook recibido: %s", event_type)

    if event_type == "checkout.session.completed":
        session            = event["data"]["object"]
        provider_pay_id    = session["id"]                          # cs_xxx
        transaction_id     = session.get("payment_intent") or session["id"]  # pi_xxx
        _handle_payment_completed(provider_pay_id, transaction_id)

    # Puedes agregar más eventos aquí según necesidad
    # elif event_type == "payment_intent.payment_failed": ...

    return jsonify({"received": True})


# ─── Errores ──────────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    logger.error("500: %s", e)
    return jsonify({"error": "Error interno del servidor"}), 500


# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 55)
    print(f"  Trujillo SafePay PRO  |  http://127.0.0.1:{SAFEPAY_PORT}")
    print(f"  Proveedor: {PAYMENT_PROVIDER}  |  DB: {DB_BACKEND}")
    print("=" * 55)
    app.run(host="0.0.0.0", port=SAFEPAY_PORT, debug=False)
