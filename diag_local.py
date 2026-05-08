import sqlite3, secrets, datetime, json

db = r"c:\Users\USUARIO\Downloads\LCA_PRO_FINAL_UNICA\data\lca_pro_final.db"
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row

user = con.execute("SELECT id FROM platform_users WHERE email='edwinsumaran3@gmail.com'").fetchone()
org  = con.execute("SELECT id FROM platform_organizations WHERE name='LCAPRO'").fetchone()

tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("TABLAS:", tables)
print("User ID:", user[0] if user else "NO ENCONTRADO")
print("Org ID:", org[0] if org else "NO ENCONTRADO")

# Ver columnas de la tabla de tokens
tok_tables = [t for t in tables if 'token' in t.lower()]
print("Tablas con 'token':", tok_tables)
if tok_tables:
    cols = [r[1] for r in con.execute(f"PRAGMA table_info({tok_tables[0]})").fetchall()]
    print(f"Columnas de {tok_tables[0]}:", cols)

con.close()
