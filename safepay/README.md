# Trujillo SafePay PRO — Microservicio independiente

Puerto: **5001**
Base de datos: `safepay/data/safepay.db` *(aislada del sistema principal)*

## Estructura

```
safepay/
├── app.py              # Flask app, puerto 5001
├── safepay_client.py   # Cliente HTTP para LCA PRO
├── requirements.txt    # Dependencias propias
├── __init__.py
├── data/
│   └── safepay.db      # SQLite aislado (se crea automáticamente)
├── templates/
│   ├── base.html
│   ├── dashboard.html
│   ├── payment_form.html
│   ├── payment_detail.html
│   └── 404.html
└── static/
    └── style.css
```

## Arranque rápido

```powershell
# Desde la raíz del proyecto:
.\start_safepay.ps1

# O manualmente:
python safepay/app.py
```

## API REST

| Método | Endpoint                        | Descripción               |
|--------|---------------------------------|---------------------------|
| GET    | `/health`                       | Health-check              |
| GET    | `/api/payments`                 | Listar pagos              |
| POST   | `/api/payment/create`           | Crear pago                |
| GET    | `/api/payment/<id>`             | Obtener pago              |
| POST   | `/api/payment/<id>/process`     | Cambiar estado            |
| GET    | `/api/stats`                    | Estadísticas globales     |

### Ejemplo: crear pago

```bash
curl -X POST http://127.0.0.1:5001/api/payment/create \
  -H "Content-Type: application/json" \
  -d '{"amount": 150.00, "method": "Yape", "customer": "Juan", "description": "Test"}'
```

### Métodos de pago soportados
`Yape` | `Plin` | `BCP` | `Interbank` | `Efectivo` | `Tarjeta`

### Estados de pago
`pendiente` → `procesando` → `completado` | `rechazado` | `reembolsado`

## Uso desde LCA PRO (app.py)

```python
from safepay.safepay_client import SafePayClient, SafePayError

client = SafePayClient()

if client.is_online():
    pay = client.create_payment(
        amount=150.00,
        method="Yape",
        description="Pago de producto #42",
        customer="Juan Pérez"
    )
    print(pay["id"])           # SP-XXXXXXXXXX
    print(pay["dashboard_url"])  # http://127.0.0.1:5001/payment/SP-...
```

## Separación de bases de datos

| Sistema        | Base de datos                     |
|----------------|-----------------------------------|
| LCA PRO        | `data/lca_pro_final.db`           |
| SafePay PRO    | `safepay/data/safepay.db`         |

No comparten conexiones ni rutas.
