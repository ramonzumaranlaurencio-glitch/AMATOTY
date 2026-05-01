import json
import datetime
# Placeholder: In production, replace with Amazon API or scraping logic

def get_trending_products(niche):
    # Simula consulta a tendencias (reemplazar por API real)
    trending = {
        "cocina": [{
            "name": "Portable Mini Blender",
            "brand": "BlendJet",
            "category": "cocina",
            "problem": "Batidos rápidos y saludables en cualquier lugar",
            "target": "Personas activas, fitness, estudiantes",
            "seo_title": "Portable Mini Blender: Batidos en segundos donde sea | Review 2026",
            "short_desc": "Lleva tu batido a cualquier parte. Potente, recargable y fácil de limpiar.",
            "article": "¿Te imaginas preparar un batido fresco en el gimnasio, la oficina o el parque? El Portable Mini Blender de BlendJet lo hace posible. Con batería recargable USB, cuchillas de acero y diseño compacto, es el gadget favorito de quienes buscan salud y practicidad. Ideal para smoothies, proteínas y jugos. Fácil de limpiar y transportar. ¡Haz tu vida más saludable hoy!",
            "hook": "¿Batido fresco en 30 segundos? Mira esto...",
            "cta": "Ver en Amazon",
            "reason": "Producto tendencia, búsquedas en aumento, excelente reseñas, utilidad real.",
            "decision": "mantener",
            "image": "https://m.media-amazon.com/images/I/61Qe0euJJZL._AC_SL1500_.jpg",
            "specs": "Marca: BlendJet, Capacidad: 475ml, Batería: 4000mAh, Material: BPA Free"
        }],
        # Agrega más nichos y productos simulados aquí
    }
    return trending.get(niche, [])

def main():
    niches = ["cocina", "hogar", "automoción", "organización", "gadgets prácticos"]
    today = datetime.date.today().isoformat()
    report = {"date": today, "products": []}
    for niche in niches:
        products = get_trending_products(niche)
        for prod in products:
            report["products"].append(prod)
    with open("docs/assets/trending_products.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("Tendencias actualizadas:", report)

if __name__ == "__main__":
    main()
