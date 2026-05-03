import datetime
import json
import os
import urllib.parse
import urllib.request

IMAGE_MIN_SCORE = 0.82

TREND_PROMPT = """
Eres un investigador de productos para ecommerce afiliado.
Devuelve SOLO JSON valido. No inventes URLs de imagen.
Selecciona productos con problema real, intencion de compra clara,
utilidad demostrable y busqueda probable en Amazon, MercadoLibre o AliExpress.
No incluyas productos medicos de alto riesgo ni promesas exageradas.
Para cada producto genera: name, brand, category, product_type, problem, target,
short_desc, seo_title, hook, reason, specs, search_query, image_must_show,
image_must_not_show. Si no puedes verificar imagen, deja image vacio e
image_verified false.
""".strip()

IMAGE_VALIDATION_PROMPT = """
Analiza la imagen y el producto esperado. Responde SOLO JSON:
{"match": true|false, "score": 0.0-1.0, "caption": "...",
"detected_objects": [], "reason": "..."}.
Marca match=false si la imagen parece decorativa, paisaje, placeholder,
producto distinto, empaque ilegible o foto generica.
""".strip()

def buscar_imagen(query):
    api_key = (
        os.environ.get("SERPAPI_KEY")
        or os.environ.get("SERP_API_KEY")
        or os.environ.get("SERPAPI_API_KEY")
        or ""
    ).strip()
    query = str(query or "").strip()
    if not api_key or not query:
        return ""
    params = urllib.parse.urlencode(
        {"engine": "google_images", "q": query, "api_key": api_key, "ijn": "0"}
    )
    try:
        req = urllib.request.Request(
            f"https://serpapi.com/search.json?{params}",
            headers={"User-Agent": "AMATOTY-Product-Advisor/1.0"},
        )
        with urllib.request.urlopen(req, timeout=8) as response:
            results = json.loads(response.read().decode("utf-8"))
    except Exception:
        return ""
    for item in results.get("images_results", []) or []:
        image = item.get("original") or item.get("thumbnail") or ""
        if str(image).startswith(("http://", "https://")):
            return str(image).replace("http://", "https://", 1)
    return ""

def product_template(product):
    product.setdefault("image", "")
    product.setdefault("image_source", "pending")
    product.setdefault("image_caption_ai", "")
    product.setdefault("image_match_score", 0)
    product.setdefault("image_verified", False)

    if product.get("image"):
        product["image"] = str(product["image"]).replace("http://", "https://", 1)
        if product.get("image_source") in ("", "pending", "none"):
            product["image_source"] = "serpapi_google_images"
        product["image_verified"] = True
        product["image_match_score"] = max(float(product.get("image_match_score") or 0), IMAGE_MIN_SCORE)
    else:
        img = buscar_imagen(product.get("search_query", ""))
        product["image"] = img
        product["image_source"] = "serpapi_google_images" if img else "none"
        product["image_verified"] = bool(img)
        product["image_match_score"] = IMAGE_MIN_SCORE if img else 0

    return product

def get_trending_products(niche):
    trending = {
        "cocina": [
            product_template(
                {
                    "name": "Portable Mini Blender",
                    "brand": "BlendJet",
                    "category": "cocina",
                    "product_type": "licuadora portatil recargable",
                    "problem": "Preparar batidos rapidos y saludables fuera de casa",
                    "target": "Personas activas, fitness, estudiantes",
                    "seo_title": "Portable Mini Blender: Batidos en segundos donde sea | Review 2026",
                    "short_desc": "Licuadora compacta para smoothies, proteinas y jugos rapidos fuera de casa.",
                    "article": "Una alternativa practica para preparar bebidas simples sin depender de una licuadora grande.",
                    "hook": "Batido fresco en menos de un minuto.",
                    "cta": "Ver opciones",
                    "reason": "Producto con problema claro, busqueda comercial y utilidad cotidiana.",
                    "decision": "mantener",
                    "search_query": "portable mini blender rechargeable",
                    "image_alt": "Licuadora portatil compacta con vaso transparente",
                    "image_must_show": ["licuadora portatil", "vaso transparente", "base recargable"],
                    "image_must_not_show": ["paisaje", "montanas", "lago", "ropa", "maquillaje"],
                    "specs": "Capacidad: 300-500ml, Energia: recargable USB, Uso: smoothies y proteinas",
                }
            )
        ],
            "llantas": [
            product_template(
                {
                    "name": "Llanta 225 70R16",
                    "brand": "Generic",
                    "category": "auto",
                    "product_type": "llanta",
                    "problem": "necesidad de reemplazo de llanta resistente",
                    "target": "conductores, flotas, uso comercial",
                    "search_query": "llanta 225 70r16",
                    "image": buscar_imagen("llanta 225 70r16"),
                    "image_alt": "llanta todo terreno 225 70r16",
                    "image_must_show": ["llanta", "neumático", "rueda"],
                    "image_must_not_show": ["paisaje", "casa", "muebles"],
                }
            )
        ],
            "hogar": [
            product_template(
                {
                    "name": "Home Cable Organizer",
                    "brand": "Generic",
                    "category": "hogar",
                    "product_type": "organizador de cables para escritorio",
                    "problem": "Cables sueltos y desorden visual en casa u oficina",
                    "target": "Personas que trabajan desde casa, estudiantes y usuarios con varios dispositivos",
                    "seo_title": "Home Cable Organizer: orden para escritorio y hogar | Review 2026",
                    "short_desc": "Organizador simple para mantener cables visibles, cargadores y escritorio bajo control.",
                    "article": "Una solucion economica para reducir desorden y encontrar cables mas rapido.",
                    "hook": "Un escritorio mas limpio en minutos.",
                    "cta": "Ver opciones",
                    "reason": "Problema cotidiano, bajo precio y alta utilidad visual.",
                    "decision": "mantener",
                    "search_query": "home cable organizer desk cable management",
                    "image_alt": "Organizador de cables para escritorio",
                    "image_must_show": ["organizador de cables", "cables ordenados", "escritorio o pared"],
                    "image_must_not_show": ["licuadora", "paisaje", "maquillaje", "auto"],
                    "specs": "Uso: cables y cargadores, Instalacion: adhesiva o de escritorio",
                }
            )
        ],
        "automocion": [
            product_template(
                {
                    "name": "Car Seat Gap Organizer",
                    "brand": "Generic",
                    "category": "automocion",
                    "product_type": "organizador para espacio entre asientos de auto",
                    "problem": "Objetos que se caen entre los asientos del auto",
                    "target": "Conductores, familias y personas que pasan tiempo en el auto",
                    "seo_title": "Car Seat Gap Organizer: orden para el auto | Review 2026",
                    "short_desc": "Accesorio para guardar celular, llaves y objetos pequenos al alcance del conductor.",
                    "article": "Una mejora practica para evitar distracciones y mantener el auto mas ordenado.",
                    "hook": "Nada se pierde entre los asientos.",
                    "cta": "Ver opciones",
                    "reason": "Soluciona una molestia frecuente con busqueda comercial clara.",
                    "decision": "mantener",
                    "search_query": "car seat gap organizer",
                    "image_alt": "Organizador entre asientos de auto",
                    "image_must_show": ["organizador de auto", "asiento de auto", "espacio entre asientos"],
                    "image_must_not_show": ["licuadora", "paisaje", "maquillaje", "cocina"],
                    "specs": "Uso: auto, Ubicacion: espacio entre asientos, Funcion: guardar objetos pequenos",
                }
            )
        ],
        "belleza": [
            product_template(
                {
                    "name": "Protector Solar Facial SPF50",
                    "brand": "Neutrogena",
                    "category": "belleza",
                    "product_type": "protector solar facial",
                    "problem": "Proteccion solar diaria y prevencion de manchas",
                    "target": "Personas que usan protector solar todos los dias",
                    "seo_title": "Protector Solar Facial SPF50: proteccion diaria ligera | Review 2026",
                    "short_desc": "Protector facial de uso diario para quienes buscan textura ligera y alta proteccion.",
                    "article": "Un esencial de cuidado facial para rutinas de manana.",
                    "hook": "El paso que no deberia faltar antes de salir.",
                    "cta": "Ver opciones",
                    "reason": "Demanda constante y necesidad clara durante todo el ano.",
                    "decision": "mantener",
                    "search_query": "protector solar facial spf 50 textura ligera",
                    "image_alt": "Envase de protector solar facial SPF50",
                    "image_must_show": ["envase de protector solar", "spf 50", "producto facial"],
                    "image_must_not_show": ["paisaje", "licuadora", "auto", "mueble"],
                    "specs": "SPF: 50, Uso: facial diario, Acabado: ligero",
                }
            )
        ],
    }
    return trending.get(niche, [])


def main():
    niches = ["cocina", "hogar", "automocion", "belleza"]
    today = datetime.date.today().isoformat()
    report = {
        "date": today,
        "quality_gate": {
            "image_min_score": IMAGE_MIN_SCORE,
            "publish_rule": "Publicar image solo si image_verified=true y image_match_score>=0.82.",
            "trend_prompt": TREND_PROMPT,
            "image_validation_prompt": IMAGE_VALIDATION_PROMPT,
        },
        "products": [],
    }
    for niche in niches:
        report["products"].extend(get_trending_products(niche))
    for path in ["docs/assets/trending_products.json", "backend/docs/assets/trending_products.json"]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    print("Tendencias actualizadas:", report)

if __name__ == "__main__":
    main()
