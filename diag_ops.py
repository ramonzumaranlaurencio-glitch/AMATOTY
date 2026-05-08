"""Script de diagnóstico: crea token local y prueba upload, save, y add-to-carousel."""
import sqlite3, secrets, hashlib, datetime, json, urllib.request, urllib.error

DB = r"c:\Users\USUARIO\Downloads\LCA_PRO_FINAL_UNICA\data\lca_pro_final.db"

def token_hash(t):
    return hashlib.sha256(t.encode()).hexdigest()

def make_id(prefix):
    import uuid
    return f"{prefix}_{uuid.uuid4().hex}"

# ── 1. Crear sesión de prueba ──────────────────────────────────────────────────
tok = "DIAG_" + secrets.token_urlsafe(32)
exp = (datetime.datetime.utcnow() + datetime.timedelta(days=1)).isoformat()

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
user = con.execute("SELECT id FROM platform_users WHERE email='edwinsumaran3@gmail.com'").fetchone()
uid = user[0]
sid = make_id("ses")
con.execute(
    "INSERT OR REPLACE INTO platform_sessions (id, user_id, token_hash, expires_at, created_at, last_seen_at) VALUES (?,?,?,?,?,?)",
    (sid, uid, token_hash(tok), exp, datetime.datetime.utcnow().isoformat(), datetime.datetime.utcnow().isoformat())
)
con.commit()

# Org del usuario
org = con.execute("SELECT organization_id FROM platform_memberships WHERE user_id=? AND status='active'", (uid,)).fetchone()
org_id = org[0] if org else None
print(f"Token: {tok[:30]}...")
print(f"OrgID: {org_id}")

# Obtener un producto real
prod = con.execute(
    "SELECT id, name FROM platform_products WHERE organization_id=? AND status!='archived' LIMIT 1",
    (org_id,)
).fetchone()
print(f"Producto: {prod[0]} - {prod[1]}" if prod else "Sin productos")
con.close()

BASE = "http://127.0.0.1:5050"
HEADERS = {"Authorization": f"Bearer {tok}", "X-Organization-Id": org_id, "Content-Type": "application/json"}

def api(method, path, body=None):
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read() or b"{}"), e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

print("\n=== TEST 1: GET /products (listar) ===")
resp, code = api("GET", f"/api/platform/products?organization_id={org_id}&limit=5")
print(f"  Status: {code}")
if "products" in resp:
    print(f"  Productos: {len(resp['products'])} encontrados")
    prods = resp["products"]
else:
    print(f"  Resp: {resp}")
    prods = []

print("\n=== TEST 2: POST /products (crear) ===")
new_prod = {
    "name": "TEST_DIAG_BORRAR",
    "description": "Producto de prueba",
    "price": 9.99,
    "category": "home",
    "status": "draft"
}
resp2, code2 = api("POST", "/api/platform/products", new_prod)
print(f"  Status: {code2}")
if "product" in resp2:
    new_pid = resp2["product"]["id"]
    print(f"  Creado OK: {new_pid}")
else:
    new_pid = None
    print(f"  ERROR: {resp2}")

print("\n=== TEST 3: PATCH /banner (carousel) ===")
pid = new_pid or (prods[0]["id"] if prods else None)
if pid:
    resp3, code3 = api("PATCH", f"/api/platform/products/{pid}/banner", {"carousel_01": True})
    print(f"  Status: {code3}")
    if "product" in resp3:
        meta = resp3["product"].get("metadata", {})
        print(f"  carousel_01 en resp: {meta.get('carousel_01', 'NO ENCONTRADO')}")
    else:
        print(f"  ERROR: {resp3}")
else:
    print("  Sin producto para testear")

print("\n=== TEST 4: Subir imagen (multipart) ===")
if pid:
    # Subir imagen simple (1x1 pixel PNG)
    import base64
    PNG_1x1 = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    boundary = "DiagBoundary123"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"test.png\"\r\nContent-Type: image/png\r\n\r\n".encode()
        + PNG_1x1
        + f"\r\n--{boundary}--\r\n".encode()
    )
    upload_headers = dict(HEADERS)
    upload_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    del upload_headers["Content-Type"]  # Lo volvemos a setear
    upload_headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
    req = urllib.request.Request(f"{BASE}/api/platform/products/{pid}/media", data=body, headers=upload_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            print(f"  Status: {r.status}")
            print(f"  Upload OK: {data}")
    except urllib.error.HTTPError as e:
        err = e.read()
        print(f"  Status: {e.code}")
        try:
            print(f"  ERROR: {json.loads(err)}")
        except:
            print(f"  ERROR raw: {err[:300]}")
    except Exception as ex:
        print(f"  Exception: {ex}")

print("\nDone.")
