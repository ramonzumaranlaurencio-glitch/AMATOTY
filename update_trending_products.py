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


def product_template(product):
    product.setdefault("image", "")
    product.setdefault("image_source", "pending")
    product.setdefault("image_caption_ai", "")
    product.setdefault("image_match_score", 0)
    product.setdefault("image_verified", False)
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
    }
    return trending.get(niche, [])


def main():
    niches = ["cocina", "hogar", "automocion", "organizacion", "gadgets practicos"]
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
