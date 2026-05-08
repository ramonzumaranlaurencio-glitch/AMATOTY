import sqlite3, json, os

candidates = [
    "data/lca_pro_final.db",
    "backend/data/lca_pro_final.db",
]
db_path = None
for c in candidates:
    if os.path.exists(c):
        db_path = c
        break

print("DB:", db_path)
if not db_path:
    print("No se encontro la base de datos")
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    print("\n--- ORGANIZATIONS ---")
    for o in conn.execute("SELECT id, name, status FROM platform_organizations").fetchall():
        print("  id=%s  name=%s  status=%s" % (o["id"], o["name"], o["status"]))

    print("\n--- PRODUCTS (primeros 15) ---")
    for p in conn.execute("SELECT id, name, status, metadata_json FROM platform_products LIMIT 15").fetchall():
        meta = json.loads(p["metadata_json"] or "{}")
        car_keys = {k: v for k, v in meta.items() if "carousel" in k or "banner" in k}
        print("  name=%-30s  status=%-12s  carousel=%s" % (p["name"], p["status"], car_keys))

    print("\n--- json_extract TEST (carousel_02=1) ---")
    rows = conn.execute(
        "SELECT p.name, p.status, o.status as org_status, json_extract(p.metadata_json, '$.carousel_02') as c02 "
        "FROM platform_products p "
        "JOIN platform_organizations o ON o.id = p.organization_id "
        "WHERE json_extract(p.metadata_json, '$.carousel_02') IS NOT NULL"
    ).fetchall()
    if rows:
        for r in rows:
            print("  name=%-30s  p.status=%s  o.status=%s  carousel_02=%s" % (r["name"], r["status"], r["org_status"], r["c02"]))
    else:
        print("  Ningun producto tiene carousel_02 en metadata_json")

    print("\n--- QUERY REAL del endpoint /public-products?carousel_key=carousel_02 ---")
    rows2 = conn.execute(
        "SELECT p.name, p.status, o.status as org_status, json_extract(p.metadata_json, '$.carousel_02') as c02 "
        "FROM platform_products p "
        "JOIN platform_organizations o ON o.id = p.organization_id "
        "WHERE p.status='published' AND o.status='active' AND json_extract(p.metadata_json, '$.carousel_02')=1"
    ).fetchall()
    print("  Resultado: %d productos" % len(rows2))
    for r in rows2:
        print("   -> %s" % r["name"])

    conn.close()
