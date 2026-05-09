"""
download_product_images.py
==========================
Descarga las imágenes de trending_products.json a docs/assets/products/
y actualiza las rutas en el JSON a rutas locales relativas.

Uso:
    python download_product_images.py

Las imágenes se guardan en docs/assets/products/prod_0.jpg, prod_1.jpg, etc.
El JSON se actualiza para apuntar a las rutas locales.
"""

import json
import os
import re
import sys
import time
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carpeta donde se guardan las imágenes descargadas
DEST_DIR = os.path.join(BASE_DIR, "docs", "assets", "products")

# JSONs a actualizar
JSON_PATHS = [
    os.path.join(BASE_DIR, "docs", "assets", "trending_products.json"),
    os.path.join(BASE_DIR, "backend", "docs", "assets", "trending_products.json"),
]

# Fallback por categoría si la descarga falla
CATEGORY_FALLBACK = {
    "cocina":     "assets/kitchen.jpg",
    "kitchen":    "assets/kitchen.jpg",
    "hogar":      "assets/home.jpg",
    "home":       "assets/home.jpg",
    "automocion": "assets/home.jpg",
    "automotive": "assets/home.jpg",
}
DEFAULT_FALLBACK = "assets/placeholder.png"

# Headers que simulan un browser real para evitar 403
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.walmart.com/",
}


def slugify(text: str) -> str:
    """Convierte texto a slug apto para nombre de archivo."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:40]


def download_image(url: str, dest_path: str) -> bool:
    """
    Descarga una imagen desde `url` y la guarda en `dest_path`.
    Devuelve True si tuvo éxito.
    """
    if not url or not url.startswith("http"):
        return False
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200:
                return False
            content_type = resp.headers.get("Content-Type", "")
            if "image" not in content_type and "octet" not in content_type:
                print(f"    ✗ Content-Type inesperado: {content_type}")
                return False
            data = resp.read()
            if len(data) < 1024:  # menos de 1KB = probablemente error
                return False
            with open(dest_path, "wb") as f:
                f.write(data)
        return True
    except Exception as exc:
        print(f"    ✗ Error descargando: {exc}")
        return False


def ext_from_url(url: str) -> str:
    """Extrae extensión de la URL o devuelve .jpg por defecto."""
    path = url.split("?")[0].lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".avif"]:
        if path.endswith(ext):
            return ext
    return ".jpg"


def process_json(json_path: str, dest_dir: str):
    if not os.path.exists(json_path):
        print(f"  No existe: {json_path}")
        return

    with open(json_path, encoding="utf-8-sig") as f:
        data = json.load(f)

    is_list = isinstance(data, list)
    products = data if is_list else data.get("products", [])

    ok = 0
    for idx, p in enumerate(products):
        remote_url = p.get("image", "")
        name       = p.get("name", f"product_{idx}")
        cat        = str(p.get("category", "")).lower()
        fallback   = CATEGORY_FALLBACK.get(cat, DEFAULT_FALLBACK)

        # Si ya es una ruta local, no hacer nada
        if remote_url and not remote_url.startswith("http"):
            print(f"  → [{idx}] {name[:40]} ya es local: {remote_url}")
            ok += 1
            continue

        slug      = slugify(name)
        ext       = ext_from_url(remote_url)
        filename  = f"prod_{idx:02d}_{slug}{ext}"
        dest_path = os.path.join(dest_dir, filename)
        local_rel = f"assets/products/{filename}"   # ruta relativa para HTML

        print(f"  → [{idx}] {name[:40]}")
        print(f"       URL: {remote_url[:80]}...")

        if download_image(remote_url, dest_path):
            size_kb = os.path.getsize(dest_path) // 1024
            print(f"       ✓ Guardada ({size_kb} KB) → {local_rel}")
            p["image"]        = local_rel
            p["image_source"] = "local"
            p["image_verified"] = True
            ok += 1
        else:
            print(f"       ✗ Falló descarga → usando fallback: {fallback}")
            p["image"]        = fallback
            p["image_source"] = "fallback_local"
            p["image_verified"] = False

        time.sleep(0.3)

    # Guardar JSON actualizado (sin BOM)
    out = products if is_list else {**data, "products": products}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n  ✅ {json_path}")
    print(f"     Imágenes locales: {ok}/{len(products)}")


def main():
    print("=" * 60)
    print("  download_product_images.py — Imágenes locales")
    print("=" * 60)

    # Crear carpeta destino
    os.makedirs(DEST_DIR, exist_ok=True)
    print(f"\nCarpeta destino: {DEST_DIR}\n")

    # Solo procesar el JSON principal primero (tienen los mismos datos)
    primary = JSON_PATHS[0]
    print(f"📄 Procesando: {primary}")
    process_json(primary, DEST_DIR)

    # Copiar imágenes descargadas al backend/docs también
    backend_dest = os.path.join(BASE_DIR, "backend", "docs", "assets", "products")
    os.makedirs(backend_dest, exist_ok=True)
    import shutil
    for fname in os.listdir(DEST_DIR):
        src = os.path.join(DEST_DIR, fname)
        dst = os.path.join(backend_dest, fname)
        shutil.copy2(src, dst)
    print(f"\n  Imágenes copiadas a backend/docs/assets/products/")

    # Ahora actualizar el JSON de backend con las mismas rutas locales
    print(f"\n📄 Procesando: {JSON_PATHS[1]}")
    process_json(JSON_PATHS[1], backend_dest)

    print("\n\n✅ Listo. Commiteando...")
    os.system(
        'git -C "' + BASE_DIR + '" add '
        'docs/assets/products '
        'backend/docs/assets/products '
        'docs/assets/trending_products.json '
        'backend/docs/assets/trending_products.json'
    )
    os.system(
        'git -C "' + BASE_DIR + '" commit -m '
        '"feat: imagenes de productos servidas localmente - sin hotlink"'
    )
    os.system('git -C "' + BASE_DIR + '" push')
    print("Push completado.")


if __name__ == "__main__":
    main()
