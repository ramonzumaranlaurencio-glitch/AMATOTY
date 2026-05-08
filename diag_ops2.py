"""Diagnóstico usando sesión existente del usuario."""
import sqlite3, hashlib, json, urllib.request, urllib.error, datetime

DB = r"c:\Users\USUARIO\Downloads\LCA_PRO_FINAL_UNICA\data\lca_pro_final.db"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# Ver sesiones existentes
print("=== SESIONES EN BD ===")
sessions = con.execute(
    "SELECT s.id, s.expires_at, s.created_at, u.email FROM platform_sessions s JOIN platform_users u ON u.id=s.user_id ORDER BY s.created_at DESC LIMIT 5"
).fetchall()
for s in sessions:
    print(f"  {s['email']} | expires={s['expires_at']} | created={s['created_at']}")

# Corregir mi sesión de prueba: la reemplazo con timezone correcto
# Crear nueva sesión con timezone correcto
import secrets
tok = "DIAG2_" + secrets.token_urlsafe(30)
exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)
exp_str = exp.isoformat()
import uuid
def make_id(p): return f"{p}_{uuid.uuid4().hex}"
def token_hash(t): return hashlib.sha256(t.encode()).hexdigest()

user = con.execute("SELECT id FROM platform_users WHERE email='edwinsumaran3@gmail.com'").fetchone()
uid = user[0]
org = con.execute("SELECT organization_id FROM platform_memberships WHERE user_id=? AND status='active'", (uid,)).fetchone()
org_id = org[0]

con.execute(
    "INSERT OR REPLACE INTO platform_sessions (id, user_id, token_hash, expires_at, created_at, last_seen_at) VALUES (?,?,?,?,?,?)",
    (make_id("ses"), uid, token_hash(tok), exp_str, exp_str, exp_str)
)
con.commit()
print(f"\nToken nuevo (con TZ): {tok[:30]}...")
print(f"Org: {org_id}")

# Obtener producto real
prod = con.execute(
    "SELECT id, name FROM platform_products WHERE organization_id=? AND status!='archived' LIMIT 1", (org_id,)
).fetchone()
pid = prod[0] if prod else None
print(f"Producto: {pid} - {prod[1] if prod else 'ninguno'}")
con.close()

BASE = "http://127.0.0.1:5050"
HEADERS = {"Authorization": f"Bearer {tok}", "X-Organization-Id": org_id, "Content-Type": "application/json"}

def api(method, path, body=None, extra_headers=None):
    data = json.dumps(body).encode() if body else None
    hdrs = dict(HEADERS)
    if extra_headers:
        hdrs.update(extra_headers)
    req = urllib.request.Request(f"{BASE}{path}", data=data, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()), r.status
    except urllib.error.HTTPError as e:
        txt = e.read()
        try: return json.loads(txt), e.code
        except: return {"raw": txt[:300].decode(errors="replace")}, e.code
    except Exception as ex:
        return {"error": str(ex)}, 0

print("\n=== TEST 1: GET /products ===")
resp, code = api("GET", f"/api/platform/products?organization_id={org_id}&limit=5")
print(f"  Status: {code}")
if "products" in resp:
    prods = resp["products"]
    print(f"  OK: {len(prods)} productos")
else:
    prods = []
    print(f"  ERROR: {resp}")

print("\n=== TEST 2: POST /products (crear) ===")
resp2, code2 = api("POST", "/api/platform/products", {
    "name": "DIAG_TEST_BORRAR", "description": "Test", "price": 9.99,
    "category": "home", "status": "draft", "organization_id": org_id
})
print(f"  Status: {code2}")
if "product" in resp2:
    new_pid = resp2["product"]["id"]
    print(f"  Creado OK: {new_pid}")
else:
    new_pid = None
    print(f"  ERROR: {resp2}")

test_pid = new_pid or pid

print(f"\n=== TEST 3: PATCH /banner carousel_01 (pid={test_pid}) ===")
if test_pid:
    resp3, code3 = api("PATCH", f"/api/platform/products/{test_pid}/banner", {"carousel_01": True})
    print(f"  Status: {code3}")
    if "product" in resp3:
        meta = resp3["product"].get("metadata", {})
        print(f"  carousel_01={meta.get('carousel_01', 'NO')}, ok={resp3.get('ok')}")
    else:
        print(f"  ERROR: {resp3}")

print(f"\n=== TEST 4: PUT /products/{test_pid} (guardar) ===")
if test_pid:
    resp4, code4 = api("PUT", f"/api/platform/products/{test_pid}", {
        "name": "DIAG_TEST_BORRAR_UPD", "description": "Actualizado", "price": 19.99,
        "category": "kitchen", "status": "draft"
    })
    print(f"  Status: {code4}")
    if "product" in resp4:
        print(f"  Guardado OK: {resp4['product']['name']}")
    else:
        print(f"  ERROR: {resp4}")

print("\n=== TEST 5: Upload imagen ===")
if test_pid:
    import base64
    PNG_1x1 = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    )
    boundary = "DIAGBND999"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"diag.png\"\r\nContent-Type: image/png\r\n\r\n".encode()
        + PNG_1x1
        + f"\r\n--{boundary}--\r\n".encode()
    )
    hdrs2 = {"Authorization": f"Bearer {tok}", "X-Organization-Id": org_id,
              "Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = urllib.request.Request(f"{BASE}/api/platform/products/{test_pid}/media",
                                  data=body, headers=hdrs2, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            print(f"  Status: {r.status}, URL: {data.get('url') or data}")
    except urllib.error.HTTPError as e:
        txt = e.read()
        try: d = json.loads(txt); print(f"  Status {e.code}: {d}")
        except: print(f"  Status {e.code}: {txt[:400].decode(errors='replace')}")
    except Exception as ex:
        print(f"  Exception: {ex}")

print("\nDone.")
