"""
fetch_walmart_images.py
=======================
Busca cada producto de trending_products.json en Walmart usando SerpAPI,
obtiene imagen real del CDN de Walmart (i5.walmartimages.com),
precio real, rating y URL directa del producto, y actualiza el JSON.

Uso:
    python fetch_walmart_images.py

Requisitos:
    pip install google-search-results requests
"""

import json
import os
import re
import sys
import time

try:
    from serpapi import GoogleSearch
except ImportError:
    print("ERROR: Instala serpapi con:  pip install google-search-results")
    sys.exit(1)

# ── Configuración ──────────────────────────────────────────────────────────────
SERPAPI_KEY = os.environ.get("SERPAPI_API_KEY", "3cedd66c5897ae1197d88edf71277345f27f80634e1de7f12c72e465a6e1f8b9")

# Rutas de los JSON a actualizar (docs/ y backend/docs/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATHS = [
    os.path.join(BASE_DIR, "docs", "assets", "trending_products.json"),
    os.path.join(BASE_DIR, "backend", "docs", "assets", "trending_products.json"),
]

# Imagen de respaldo local si Walmart no devuelve nada
CATEGORY_FALLBACK = {
    "cocina":      "assets/kitchen.jpg",
    "kitchen":     "assets/kitchen.jpg",
    "hogar":       "assets/home.jpg",
    "home":        "assets/home.jpg",
    "automocion":  "assets/home.jpg",
    "automotive":  "assets/home.jpg",
}
DEFAULT_FALLBACK = "assets/placeholder.png"


# ── Helpers ────────────────────────────────────────────────────────────────────

def _img_hires(url: str) -> str:
    """Sube la resolución del thumb de Walmart de 180px a 600px."""
    if not url:
        return url
    url = re.sub(r'odnHeight=\d+', 'odnHeight=600', url)
    url = re.sub(r'odnWidth=\d+',  'odnWidth=600',  url)
    # Si no tiene parámetros de tamaño, agregar
    if 'odnHeight' not in url and 'odnWidth' not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}odnHeight=600&odnWidth=600&odnBg=FFFFFF"
    return url


WMT_AFFILIATE = "https://goto.walmart.com/c/7284190/568844/9383"


def _walmart_url(product_page_url: str, item_id: str) -> str:
    """Devuelve URL de afiliado del producto en Walmart (Impact ID 7284190)."""
    if product_page_url and product_page_url.startswith("http"):
        dest = product_page_url.split("?")[0]
    elif item_id:
        dest = f"https://www.walmart.com/ip/{item_id}"
    else:
        return ""
    from urllib.parse import quote_plus
    return f"{WMT_AFFILIATE}?u={quote_plus(dest)}"


def buscar_en_walmart(query: str) -> dict:
    """
    Busca un producto en Walmart via SerpAPI.
    Devuelve: {image, price, rating, walmart_url, title, item_id}
    """
    params = {
        "engine": "walmart",
        "query": query,
        "api_key": SERPAPI_KEY,
        "num": 5,
    }
    try:
        results = GoogleSearch(params).get_dict()
    except Exception as exc:
        print(f"  ✗ SerpAPI error: {exc}")
        return {}

    organic = results.get("organic_results") or []
    if not organic:
        print(f"  ✗ Sin resultados para: {query!r}")
        return {}

    # Tomar el primer resultado con imagen
    for item in organic:
        thumb = item.get("thumbnail") or item.get("primary_image") or ""
        if not thumb:
            continue
        # El precio puede venir en primary_offer.offer_price o en price/primary_price
        primary_offer = item.get("primary_offer") or {}
        price_raw = (
            primary_offer.get("offer_price")
            or item.get("price")
            or item.get("primary_price")
            or ""
        )
        if isinstance(price_raw, (int, float)):
            price_str = f"{float(price_raw):.2f}"
        else:
            m = re.search(r"[\d]+\.?\d*", str(price_raw).replace(",", ""))
            price_str = m.group(0) if m else ""

        rating = item.get("rating") or item.get("stars") or 0
        try:
            rating = round(float(str(rating).split()[0]), 1)
        except Exception:
            rating = 0.0

        item_id  = str(item.get("item_id") or item.get("product_id") or "")
        page_url = item.get("product_page_url") or item.get("url") or ""

        return {
            "image":       _img_hires(thumb),
            "price":       price_str,
            "rating":      rating if rating > 0 else None,
            "walmart_url": _walmart_url(page_url, item_id),
            "title":       item.get("title", ""),
            "item_id":     item_id,
        }

    print(f"  ✗ Todos los resultados sin imagen para: {query!r}")
    return {}


# ── Lógica principal ───────────────────────────────────────────────────────────

def actualizar_json(json_path: str):
    if not os.path.exists(json_path):
        print(f"  No existe: {json_path}")
        return

    with open(json_path, encoding="utf-8-sig") as f:
        data = json.load(f)

    products = data if isinstance(data, list) else data.get("products", [])

    updated = 0
    for p in products:
        query    = p.get("search_query") or p.get("name") or ""
        cat      = str(p.get("category", "")).lower()
        fallback = CATEGORY_FALLBACK.get(cat, DEFAULT_FALLBACK)

        print(f"\n→ {p.get('name', '?')} | query: {query!r}")

        result = buscar_en_walmart(query)
        if not result:
            # Si no encontró nada, mantener fallback local
            if not p.get("image") or "walmartimages" not in p.get("image", ""):
                p["image"] = fallback
                p["image_verified"] = False
                p["image_source"] = "fallback_local"
            print(f"  → Usando fallback: {fallback}")
            continue

        # Actualizar campos con datos reales de Walmart
        p["image"]         = result["image"]
        p["image_verified"] = True
        p["image_source"]  = "walmart_cdn"

        if result.get("price"):
            p["price"] = result["price"]
        if result.get("rating"):
            p["rating"] = result["rating"]
        if result.get("walmart_url"):
            p["walmart_url"] = result["walmart_url"]

        print(f"  ✓ imagen: {result['image'][:80]}...")
        print(f"  ✓ precio: ${result.get('price','?')}  rating: {result.get('rating','?')}")
        print(f"  ✓ url: {result.get('walmart_url','')}")
        updated += 1

        # Pausa para no saturar la API
        time.sleep(0.8)

    # Guardar
    if isinstance(data, list):
        out = products
    else:
        data["products"] = products
        out = data

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n✅ {json_path}")
    print(f"   Actualizados: {updated}/{len(products)} productos")


def main():
    print("=" * 60)
    print("  fetch_walmart_images.py — Imágenes reales de Walmart")
    print("=" * 60)

    if not SERPAPI_KEY or SERPAPI_KEY == "TU_CLAVE_AQUI":
        print("\nERROR: Configura SERPAPI_API_KEY o edita SERPAPI_KEY en el script.")
        sys.exit(1)

    for path in JSON_PATHS:
        print(f"\n📄 Procesando: {path}")
        actualizar_json(path)

    print("\n\nListo. Ahora ejecuta:")
    print("  git add docs/assets/trending_products.json backend/docs/assets/trending_products.json")
    print('  git commit -m "feat: imagenes reales Walmart en trending products"')
    print("  git push")


if __name__ == "__main__":
    main()
