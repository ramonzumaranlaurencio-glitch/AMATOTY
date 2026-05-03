from serpapi import GoogleSearch
import datetime
import json

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

from serpapi import GoogleSearch

def buscar_imagen(query):
    params = {
        "engine": "google_images",
        "q": query,
        "api_key": "3cedd66c5897ae1197d88edf71277345f27f80634e1de7f12c72e465a6e1f8b9"
    }

    search = GoogleSearch(params)
    results = search.get_dict()

    if "images_results" in results:
        return results["images_results"][0]["original"]

    return ""

def product_template(product):
    product.setdefault("image", "")
    product.setdefault("image_source", "pending")
    product.setdefault("image_caption_ai", "")
    product.setdefault("image_match_score", 0)
    product.setdefault("image_verified", False)

    if product.get("image") == "":
        img = buscar_imagen(product.get("search_query", ""))
        product["image"] = img
        product["image_source"] = "serpapi" if img else "none"

    return product

def get_trending_products(niche):
    trending = {
        
                "seguridad": [
            product_template({
                "name": "Extintor portátil ABC",
                "brand": "Generic",
                "category": "seguridad",
                "product_type": "extintor",
                "problem": "riesgo de incendio",
                "target": "hogar, autos, oficinas",
                "search_query": "extintor contra incendios ABC",
                "image": "",
                "image_alt": "extintor rojo",
                "image_must_show": ["extintor", "rojo", "cilindro"],
                "image_must_not_show": ["paisaje", "muebles"]
            })
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
    with open("docs/assets/trending_products.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("Tendencias actualizadas:", report)

if __name__ == "__main__":
    main()

