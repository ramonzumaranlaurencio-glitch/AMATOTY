"""
safepay_client.py
─────────────────
Cliente HTTP para llamar al microservicio Trujillo SafePay PRO
desde el sistema principal LCA PRO (app.py).

Uso:
    from safepay.safepay_client import SafePayClient

    client = SafePayClient()

    # Verificar disponibilidad
    if client.is_online():
        pay = client.create_payment(amount=150.00, method="Yape",
                                    description="Compra #123", customer="Juan")
        print(pay["id"])          # SP-XXXX
        print(pay["dashboard_url"])

    # Consultar estado
    status = client.get_payment("SP-XXXX")

    # Procesar / cambiar estado
    client.process_payment("SP-XXXX", status="completado", notes="Yape confirmado")

    # Listar todos
    payments = client.list_payments()
    payments_pen = client.list_payments(status="pendiente")
"""

from __future__ import annotations

import logging
import os
from typing import Any

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger("safepay_client")

SAFEPAY_BASE_URL = os.getenv("SAFEPAY_API_URL") or os.getenv("SAFEPAY_URL") or "http://127.0.0.1:5001"
TIMEOUT          = 5  # segundos


class SafePayError(Exception):
    """Error al comunicarse con SafePay."""


class SafePayClient:
    """Cliente para el microservicio SafePay PRO."""

    def __init__(self, base_url: str = SAFEPAY_BASE_URL, timeout: int = TIMEOUT):
        if requests is None:
            raise ImportError("Instala 'requests': pip install requests")
        self.base = base_url.rstrip("/")
        self.timeout = timeout

    # ── Helpers internos ───────────────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> Any:
        try:
            resp = requests.get(
                f"{self.base}{path}", params=params, timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            raise SafePayError(
                "SafePay no disponible. ¿Está corriendo en http://127.0.0.1:5001?"
            )
        except requests.exceptions.Timeout:
            raise SafePayError("SafePay tardó demasiado en responder.")
        except requests.exceptions.HTTPError as e:
            raise SafePayError(f"SafePay respondió con error: {e.response.status_code}")

    def _post(self, path: str, json_body: dict) -> Any:
        try:
            resp = requests.post(
                f"{self.base}{path}", json=json_body, timeout=self.timeout
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.ConnectionError:
            raise SafePayError(
                "SafePay no disponible. ¿Está corriendo en http://127.0.0.1:5001?"
            )
        except requests.exceptions.Timeout:
            raise SafePayError("SafePay tardó demasiado en responder.")
        except requests.exceptions.HTTPError as e:
            raise SafePayError(f"SafePay respondió con error: {e.response.status_code}")

    # ── API pública ────────────────────────────────────────────────────────────

    def is_online(self) -> bool:
        """Devuelve True si SafePay está activo."""
        try:
            data = self._get("/health")
            return data.get("status") == "ok"
        except SafePayError:
            return False

    def create_payment(
        self,
        amount: float,
        method: str,
        currency: str = "PEN",
        description: str = "",
        customer: str = "",
        metadata: dict | None = None,
    ) -> dict:
        """
        Crea un nuevo pago en SafePay.
        Retorna dict con: id, status, amount, currency, method, dashboard_url
        """
        return self._post(
            "/api/payment/create",
            {
                "amount": amount,
                "currency": currency,
                "method": method,
                "description": description,
                "customer": customer,
                "metadata": metadata or {},
            },
        )

    def get_payment(self, pay_id: str) -> dict:
        """Obtiene los datos de un pago por ID."""
        return self._get(f"/api/payment/{pay_id}")

    def process_payment(
        self, pay_id: str, status: str, notes: str = ""
    ) -> dict:
        """
        Cambia el estado de un pago.
        status válidos: pendiente | procesando | completado | rechazado | reembolsado
        """
        return self._post(
            f"/api/payment/{pay_id}/process",
            {"status": status, "notes": notes},
        )

    def list_payments(self, status: str | None = None) -> list[dict]:
        """Lista los pagos. Filtra por status si se especifica."""
        params = {"status": status} if status else None
        return self._get("/api/payments", params=params)

    def stats(self) -> dict:
        """Estadísticas globales del servicio."""
        return self._get("/api/stats")

    def dashboard_url(self, pay_id: str | None = None) -> str:
        """URL del dashboard de SafePay (con pago específico si se pasa ID)."""
        if pay_id:
            return f"{self.base}/payment/{pay_id}"
        return f"{self.base}/dashboard"
