import requests
import datetime
import json

API_URL = "http://localhost:8000/trending-products"

# Simula consulta a Google Trends, Amazon, TikTok, etc.
def fetch_trends():
    # Aquí deberías integrar pytrends, scraping, o APIs reales
    return [
        {
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
        }
    ]

def update_products():
    products = fetch_trends()
    for prod in products:
        r = requests.post("http://localhost:8000/update-product", json=prod)
        print(f"Actualizado: {prod['name']} - status: {r.status_code}")

if __name__ == "__main__":
    update_products()
