"""
fix_hub_images.py
=================
Busca imágenes reales en Walmart para cada producto de HUB_SECTIONS,
las descarga en docs/assets/products/hub/ y actualiza los img:"..." 
directamente en smart-search.html con rutas locales.
"""

import json
import os
import re
import shutil
import time
import urllib.request

try:
    from serpapi import GoogleSearch
    HAS_SERPAPI = True
except ImportError:
    HAS_SERPAPI = False
    print("WARN: serpapi no disponible, usando imágenes locales existentes")

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
DEST_DIR  = os.path.join(BASE_DIR, "docs", "assets", "products", "hub")
HTML_PATH = os.path.join(BASE_DIR, "docs", "smart-search.html")
HTML_BACKEND = os.path.join(BASE_DIR, "backend", "docs", "smart-search.html")

SERPAPI_KEY = os.environ.get("SERPAPI_API_KEY",
    "3cedd66c5897ae1197d88edf71277345f27f80634e1de7f12c72e465a6e1f8b9")

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

# Todos los productos del HUB con su search_query
HUB_PRODUCTS = [
    # trending
    {"name":"Portable Mini Blender",        "q":"portable mini blender usb rechargeable"},
    {"name":"Car Seat Gap Organizer",        "q":"car seat gap organizer"},
    {"name":"Mini Vacuum Cleaner",           "q":"mini handheld vacuum cleaner cordless"},
    {"name":"Home Cable Organizer",          "q":"cable organizer clips desk"},
    {"name":"Kitchen Food Saver",            "q":"kitchen food saver vacuum sealer"},
    {"name":"LED Strip Lights 10ft",         "q":"led strip lights color changing rgb"},
    # tiktok
    {"name":"Ice Roller Face Massager",      "q":"ice roller face massager"},
    {"name":"Cleaning Gel Putty",            "q":"cleaning gel putty keyboard"},
    {"name":"Gua Sha Facial Tool",           "q":"gua sha facial tool jade"},
    {"name":"Cloud Slippers",               "q":"cloud slippers memory foam"},
    {"name":"Sunrise Alarm Clock",           "q":"sunrise alarm clock light therapy"},
    {"name":"Aesthetic Desk Lamp",           "q":"wireless charging desk lamp"},
    # home
    {"name":"Air Fryer 5.8Qt",              "q":"air fryer 5.8 quart"},
    {"name":"Instant Pot 6Qt Duo",          "q":"instant pot duo 6 quart"},
    {"name":"Robot Vacuum Cleaner",          "q":"robot vacuum cleaner self charging"},
    {"name":"Weighted Blanket 15lb",         "q":"weighted blanket 15 pound queen"},
    {"name":"Smart Plug 4-Pack",            "q":"smart plug wifi alexa 4 pack"},
    {"name":"Dish Drying Rack 2-Tier",       "q":"2 tier dish drying rack stainless steel"},
    # industrial
    {"name":"Cordless Drill Set 20V",        "q":"cordless drill set 20v brushless"},
    {"name":"Laser Level Self-Leveling",     "q":"laser level self leveling 360"},
    {"name":"Socket Set 230-Piece",          "q":"socket set 230 piece chrome vanadium"},
    {"name":"Digital Multimeter",            "q":"digital multimeter auto ranging"},
    {"name":"Stud Finder Wall Scanner",      "q":"stud finder wall scanner 6 in 1"},
    {"name":"Work Light LED 60W",            "q":"led work light 60w tripod"},
    # tech
    {"name":"Wireless Earbuds ANC",          "q":"wireless earbuds active noise canceling"},
    {"name":"Portable Charger 26800mAh",     "q":"portable charger 26800mah fast charge"},
    {"name":"Smart Watch Fitness Tracker",   "q":"smartwatch fitness tracker gps heart rate"},
    {"name":"USB-C Hub 7-in-1",             "q":"usb c hub 7 in 1 4k hdmi"},
    {"name":"Webcam 4K HD",                 "q":"webcam 4k hd auto focus microphone"},
    {"name":"Mechanical Keyboard RGB",       "q":"mechanical keyboard rgb tkl tenkeyless"},
    # fitness
    {"name":"Resistance Bands Set 5pc",      "q":"resistance bands set 5 piece workout"},
    {"name":"Adjustable Dumbbell 25lb",      "q":"adjustable dumbbell 25 lb dial"},
    {"name":"Yoga Mat Extra Thick",         "q":"yoga mat extra thick non slip"},
    {"name":"Jump Rope Speed Cable",         "q":"jump rope speed cable ball bearing"},
    {"name":"Pull Up Bar Doorframe",         "q":"pull up bar doorframe no screws"},
    {"name":"Ab Roller Wheel",              "q":"ab roller wheel core workout"},
    # amazon
    {"name":"Echo Dot 5th Gen",              "q":"echo dot 5th gen smart speaker"},
    {"name":"Fire TV Stick 4K Max",          "q":"fire tv stick 4k max"},
    {"name":"Kindle Paperwhite 2023",        "q":"kindle paperwhite 2023"},
    {"name":"Ring Video Doorbell",           "q":"ring video doorbell wired"},
    {"name":"iRobot Roomba i4",             "q":"irobot roomba i4 wifi robot vacuum"},
    {"name":"Bose QuietComfort 45",          "q":"bose quietcomfort 45 wireless headphones"},
    # walmart
    {"name":"Onn 55in 4K Roku TV",           "q":"55 inch 4k smart tv roku"},
    {"name":"Equate Blood Pressure Monitor", "q":"blood pressure monitor arm automatic"},
    {"name":"Mainstays 7 Piece Bed Set",     "q":"queen comforter set 7 piece"},
    {"name":"Better Homes Air Fryer 5.3Qt",  "q":"air fryer 5.3 qt digital"},
    {"name":"Blackweb Gaming Headset",       "q":"gaming headset 7.1 surround sound usb rgb"},
    {"name":"Hyper Tough 20V Drill",         "q":"20v cordless drill bit set"},
]


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text[:36]


def img_hires(url):
    if not url: return url
    url = re.sub(r'odnHeight=\d+', 'odnHeight=600', url)
    url = re.sub(r'odnWidth=\d+',  'odnWidth=600',  url)
    if 'odnHeight' not in url and 'odnWidth' not in url:
        sep = '&' if '?' in url else '?'
        url = f"{url}{sep}odnHeight=600&odnWidth=600&odnBg=FFFFFF"
    return url


def fetch_walmart_img(query):
    if not HAS_SERPAPI:
        return None
    params = {
        "engine": "walmart",
        "query": query,
        "api_key": SERPAPI_KEY,
        "num": 5,
    }
    try:
        results = GoogleSearch(params).get_dict()
    except Exception as e:
        print(f"    SerpAPI error: {e}")
        return None
    for item in (results.get("organic_results") or []):
        thumb = item.get("thumbnail") or item.get("primary_image") or ""
        if thumb:
            return img_hires(thumb)
    return None


def download_image(url, dest_path):
    if not url or not url.startswith("http"):
        return False
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status != 200: return False
            data = resp.read()
            if len(data) < 2000: return False
            with open(dest_path, "wb") as f:
                f.write(data)
        return True
    except Exception as e:
        print(f"    Descarga falló: {e}")
        return False


def main():
    os.makedirs(DEST_DIR, exist_ok=True)
    backend_dest = os.path.join(BASE_DIR, "backend", "docs", "assets", "products", "hub")
    os.makedirs(backend_dest, exist_ok=True)

    # Mapa nombre → local_path
    name_to_local = {}

    print(f"Procesando {len(HUB_PRODUCTS)} productos del hub...\n")

    for idx, prod in enumerate(HUB_PRODUCTS):
        name     = prod["name"]
        query    = prod["q"]
        slug     = slugify(name)
        filename = f"hub_{idx:02d}_{slug}.jpeg"
        dest     = os.path.join(DEST_DIR, filename)
        local    = f"assets/products/hub/{filename}"

        print(f"[{idx+1:02d}/{len(HUB_PRODUCTS)}] {name}")

        # Si ya existe, saltear descarga
        if os.path.exists(dest) and os.path.getsize(dest) > 2000:
            print(f"  → Ya existe ({os.path.getsize(dest)//1024}KB)")
            name_to_local[name] = local
            shutil.copy2(dest, os.path.join(backend_dest, filename))
            continue

        # Buscar en Walmart
        url = fetch_walmart_img(query)
        if url:
            print(f"  → URL: {url[:70]}...")
            if download_image(url, dest):
                sz = os.path.getsize(dest) // 1024
                print(f"  ✓ Guardada ({sz}KB)")
                name_to_local[name] = local
                shutil.copy2(dest, os.path.join(backend_dest, filename))
            else:
                print(f"  ✗ Descarga falló")
                name_to_local[name] = None
        else:
            print(f"  ✗ Sin resultado en Walmart")
            name_to_local[name] = None

        time.sleep(0.6)

    print(f"\nImágenes descargadas: {sum(1 for v in name_to_local.values() if v)}/{len(HUB_PRODUCTS)}")

    # Actualizar img:"..." en smart-search.html
    print(f"\nActualizando {HTML_PATH}...")
    with open(HTML_PATH, encoding="utf-8") as f:
        html = f.read()

    replaced = 0
    for name, local in name_to_local.items():
        if not local:
            continue
        # Buscar el producto por nombre y reemplazar su img:"..."
        # Patrón: {name:"NOMBRE", ... img:"CUALQUIER_COSA", ...}
        escaped_name = re.escape(name)
        # Reemplaza img:"..." dentro de la misma línea del producto
        # El bloque del producto está en una sola línea, así que buscamos la línea
        def replacer(m):
            line = m.group(0)
            # Reemplazar img:"..." en esa línea
            new_line = re.sub(r'img:"[^"]*"', f'img:"{local}"', line)
            return new_line
        
        pattern = rf'(\{{[^\}}]*?name:"{escaped_name}"[^\}}]*?\}})'
        new_html, n = re.subn(pattern, replacer, html, flags=re.DOTALL)
        if n:
            html = new_html
            replaced += n
            print(f"  ✓ {name} → {local}")
        else:
            print(f"  ? No encontrado en HTML: {name}")

    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    shutil.copy2(HTML_PATH, HTML_BACKEND)
    print(f"\nHTML actualizado: {replaced} productos")

    # Git commit
    print("\nCommiteando...")
    cmds = [
        f'git -C "{BASE_DIR}" add docs/assets/products/hub backend/docs/assets/products/hub docs/assets/placeholder.png backend/docs/assets/placeholder.png docs/smart-search.html backend/docs/smart-search.html',
        f'git -C "{BASE_DIR}" commit -m "fix: imagenes locales para todos los productos del hub - sin amazon CDN"',
        f'git -C "{BASE_DIR}" push',
    ]
    for cmd in cmds:
        print(f"  $ {cmd}")
        os.system(cmd)
    print("\n✅ Listo")


if __name__ == "__main__":
    main()
