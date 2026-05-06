import json
import os
import re
import sqlite3
import sys
import traceback
import unicodedata
import urllib.parse
import urllib.request
import uuid
from io import BytesIO
from datetime import datetime

from flask import jsonify, request, send_from_directory
from flask import Flask
from flask_cors import CORS
from PIL import Image

from product_platform import init_platform_db, platform_bp

app = Flask(__name__)
CORS(app)
app.register_blueprint(platform_bp)
init_platform_db()

IMAGE_MIN_SCORE = 0.82
IMAGE_VALIDATION_PROMPT = (
    "Analiza la imagen y el producto esperado. Haz OCR sobre textos, placas, "
    "etiquetas, codigos de modelo y empaque. Responde SOLO JSON con match, "
    "score, caption, detected_objects, detected_text, detected_brand, "
    "detected_model y reason. Marca match=false si la imagen parece decorativa, "
    "paisaje, placeholder, producto distinto, empaque ilegible, foto generica "
    "o si hay conflicto entre texto detectado y producto esperado."
)
UNIVERSAL_VISUAL_AGENT_PROMPT = (
    "Rol: Eres un Agente de Inteligencia Visual experto en reconocimiento de "
    "productos a nivel global y estratega de ventas. Tarea: analiza la imagen "
    "y detecta todos los productos presentes. Para cada producto identificado, "
    "extrae atributos unicos sin importar categoria: tecnologia, hogar, "
    "construccion, moda, belleza, cocina, automocion, herramientas, consumo "
    "masivo u otra. Identifica marca, modelo, color, material, estado, textos "
    "visibles mediante OCR, industria/categoria dinamica, uso principal, "
    "publico objetivo y propuesta de valor. Responde exclusivamente JSON valido."
)
MONEDAS = {
    "PE": ("S/", 1.0),
    "MX": ("MXN", 1.0),
    "CL": ("CLP", 1.0),
    "CO": ("COP", 1.0),
    "AR": ("ARS", 1.0),
    "US": ("USD", 1.0),
    "EC": ("USD", 1.0),
    "BO": ("BOB", 1.0),
    "PY": ("PYG", 1.0),
    "UY": ("UYU", 1.0),
    "BR": ("BRL", 1.0),
    "VE": ("VES", 1.0),
    "OTRO": ("USD", 1.0),
}

CULTURA = {
    "PE": {"carrito": "carrito", "btn_agregar": "Agregar al carrito"},
    "MX": {"carrito": "carrito", "btn_agregar": "Anadir al carrito"},
    "CL": {"carrito": "carrito", "btn_agregar": "Agregar al carrito"},
    "CO": {"carrito": "canasta", "btn_agregar": "Agregar a la canasta"},
    "AR": {"carrito": "canasta", "btn_agregar": "Sumar a la canasta"},
    "US": {"carrito": "cart", "btn_agregar": "Add to cart"},
    "EC": {"carrito": "carrito", "btn_agregar": "Agregar al carrito"},
    "BO": {"carrito": "carrito", "btn_agregar": "Agregar al carrito"},
    "PY": {"carrito": "carrito", "btn_agregar": "Agregar al carrito"},
    "UY": {"carrito": "carrito", "btn_agregar": "Agregar al carrito"},
    "BR": {"carrito": "carrinho", "btn_agregar": "Adicionar ao carrinho"},
    "VE": {"carrito": "carrito", "btn_agregar": "Agregar al carrito"},
    "OTRO": {"carrito": "carrito", "btn_agregar": "Agregar al carrito"},
}

SMART_MIN_OPTIONS = 0
SMART_LIVE_SEARCH_LIMIT = 12
FX_TO_USD = {
    "USD": 1.0,
    "PEN": 1 / 3.75,
    "COP": 1 / 3900,
    "MXN": 1 / 17,
    "CLP": 1 / 930,
    "ARS": 1 / 1050,
    "BOB": 1 / 6.9,
    "PYG": 1 / 7300,
    "UYU": 1 / 39,
    "BRL": 1 / 5,
}

SHOPPING_FAMILIES = [
    {
        "key": "lavadora",
        "terms": [
            "lavadora",
            "lavarropa",
            "lavarropas",
            "lavaseca",
            "washing machine",
            "washer",
            "washer dryer",
        ],
        "category": "electrodomesticos",
        "product_type": "lavadora",
        "sector": "hogar",
        "problem": "lavar ropa con mejor capacidad, ahorro de tiempo y ciclos adecuados",
        "target": "hogares, apartamentos, lavanderias pequenas y compradores que comparan capacidad",
        "material": "acero/plastico",
        "compatibility": "capacidad en kg o pies cubicos, carga frontal/superior, voltaje y espacio disponible",
        "templates": [
            ("Midea 7 kg carga superior", "Midea", 285, "Capacidad: 7 kg, Carga: superior, Uso: hogar pequeno", "economy"),
            ("Whirlpool 8 kg carga superior", "Whirlpool", 360, "Capacidad: 8 kg, Carga: superior, Programas: basicos", "professional"),
            ("Samsung 9 kg carga superior", "Samsung", 430, "Capacidad: 9 kg, Carga: superior, Motor: inverter por validar", "professional"),
            ("LG 8 kg carga frontal inverter", "LG", 520, "Capacidad: 8 kg, Carga: frontal, Motor: inverter", "professional"),
            ("Electrolux 10 kg carga superior", "Electrolux", 610, "Capacidad: 10 kg, Carga: superior, Uso: familiar", "professional"),
            ("GE 4.5 cu ft carga superior", "GE", 690, "Capacidad: 4.5 cu ft, Carga: superior, Uso: familiar", "professional"),
            ("Bosch Serie 300 carga frontal", "Bosch", 780, "Carga: frontal, Segmento: premium compacto, Uso: apartamento", "premium"),
            ("Maytag 4.7 cu ft alta eficiencia", "Maytag", 870, "Capacidad: 4.7 cu ft, Tipo: alta eficiencia, Uso: familiar", "premium"),
            ("Samsung Bespoke 5.3 cu ft", "Samsung", 1040, "Capacidad: 5.3 cu ft, Tipo: smart washer, Uso: alto volumen", "premium"),
            ("LG WashTower lavadora/secadora", "LG", 1450, "Tipo: torre lavadora secadora, Uso: combo premium, Espacio: vertical", "premium"),
        ],
    }
]


def _data_path(*parts):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", *parts))


SITE_DIR = _data_path("docs")
LOCAL_SITE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "docs"))

# DATA_DIR permite apuntar a un disco persistente en Render/Railway/etc.
# Ej: DATA_DIR=/var/data
_DATA_DIR_ENV = os.environ.get("DATA_DIR", "")
if _DATA_DIR_ENV:
    TRACKING_DB_PATH = os.path.join(_DATA_DIR_ENV, "lca_pro_final.db")
else:
    TRACKING_DB_PATH = _data_path("data", "lca_pro_final.db")

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

# URL del microservicio SafePay.
# Prioridad: variable de entorno SAFEPAY_API_URL > SAFEPAY_URL > URL de producción por defecto.
# En local, levanta el microservicio en http://127.0.0.1:5001.
# Seguridad: rechazar si no empieza con http (ej: postgresql:// por error de config en Render)
_safepay_raw = os.getenv("SAFEPAY_API_URL") or os.getenv("SAFEPAY_URL") or ""
if not _safepay_raw or not _safepay_raw.startswith("http"):
    _safepay_raw = "https://amatoty-1.onrender.com"
SAFEPAY_API_URL = _safepay_raw.rstrip("/")

GEMINI_DIAGNOSTICO_SCHEMA = {
    "type": "object",
    "properties": {
        "rostro_detectado": {"type": "boolean"},
        "calidad_foto": {
            "type": "object",
            "properties": {
                "iluminacion": {"type": "string"},
                "nitidez": {"type": "string"},
                "angulo": {"type": "string"},
                "observaciones": {"type": "string"},
            },
            "required": ["iluminacion", "nitidez", "angulo", "observaciones"],
        },
        "tipo_piel": {"type": "string"},
        "subtono": {"type": "string"},
        "nivel_grasa": {"type": "string"},
        "nivel_hidratacion": {"type": "string"},
        "textura": {"type": "string"},
        "ojeras": {"type": "string"},
        "sensibilidad": {"type": "string"},
        "manchas_o_tono": {"type": "string"},
        "labios": {"type": "string"},
        "confianza": {"type": "number"},
        "recomendacion": {"type": "string"},
        "rutina_manana": {
            "type": "array",
            "items": {"type": "string"},
        },
        "rutina_noche": {
            "type": "array",
            "items": {"type": "string"},
        },
        "ingredientes_recomendados": {
            "type": "array",
            "items": {"type": "string"},
        },
        "evitar": {
            "type": "array",
            "items": {"type": "string"},
        },
        "maquillaje_sugerido": {
            "type": "object",
            "properties": {
                "base": {"type": "string"},
                "polvo": {"type": "string"},
                "rubor": {"type": "string"},
                "labial": {"type": "string"},
            },
            "required": ["base", "polvo", "rubor", "labial"],
        },
        "resumen_venta": {"type": "string"},
    },
    "required": [
        "rostro_detectado",
        "calidad_foto",
        "tipo_piel",
        "subtono",
        "nivel_grasa",
        "nivel_hidratacion",
        "textura",
        "ojeras",
        "sensibilidad",
        "manchas_o_tono",
        "labios",
        "confianza",
        "recomendacion",
        "rutina_manana",
        "rutina_noche",
        "ingredientes_recomendados",
        "evitar",
        "maquillaje_sugerido",
        "resumen_venta",
    ],
}

GEMINI_DIAGNOSTICO_PROMPT = """
Eres Oye Bonita, una asesora visual experta en belleza, piel y venta consultiva.
Analiza SOLO lo visible en la foto. No inventes datos medicos ni diagnostiques
enfermedades. Tu tarea es producir un diagnostico cosmetico practico y diferente
para cada imagen.

Evalua con detalle:
- presencia de rostro, iluminacion, nitidez, angulo y sombras;
- tipo de piel aparente: seca, grasa, mixta, normal o sensible;
- subtono aparente: frio, calido, neutro u oliva;
- brillo en zona T, resequedad, textura, poros visibles, ojeras, tono desigual,
  labios y sensibilidad aparente;
- rutina de manana, rutina de noche, ingredientes utiles y que evitar;
- maquillaje sugerido: base, polvo, rubor y labial.

Reglas:
- Si la foto no permite ver bien el rostro, dilo en calidad_foto y baja confianza.
- Cada campo debe responder a esa imagen, no uses una plantilla fija.
- Responde en espanol latino, claro y comercial.
- Devuelve exclusivamente JSON valido con el schema solicitado.
"""


@app.errorhandler(Exception)
def handle_unexpected_error(exc):
    return (
        jsonify(
            {
                "error": "Error interno del backend.",
                "detail": str(exc),
                "analysis_mode": "error",
            }
        ),
        500,
    )


def _fallback_oye_bonita_html():
    return """<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Oye Bonita - Diagnostico Facial</title>
  <style>
    body{margin:0;background:#f8fafc;color:#1f2937;font-family:Arial,sans-serif}
    .wrap{max-width:840px;margin:32px auto;padding:0 16px}
    .card{background:#fff7ed;border:1px solid #fed7aa;border-radius:16px;padding:24px;box-shadow:0 8px 28px #0001}
    h1{margin:0 0 16px;color:#d81b60;text-align:center}
    label{font-weight:700} select,input{margin:8px 0 16px;padding:8px;width:100%;max-width:360px}
    button{background:#d81b60;color:white;border:0;border-radius:8px;padding:11px 18px;font-weight:700;cursor:pointer}
    button:disabled{background:#e5e7eb;color:#777}.msg{background:#f1f5f9;border-radius:10px;padding:12px;margin:16px 0}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px}.prod{background:white;border-radius:12px;padding:12px;text-align:center;border:1px solid #e5e7eb}
    .prod img{width:100px;height:100px;object-fit:cover;border-radius:8px}
  </style>
</head>
<body>
  <main class="wrap">
    <section class="card">
      <h1>Oye Bonita: Diagnostico Facial</h1>
      <label for="pais">Pais</label><br>
      <select id="pais"><option value="PE">Peru</option><option value="MX">Mexico</option><option value="CO">Colombia</option><option value="US">Estados Unidos</option><option value="OTRO">Otro</option></select><br>
      <label for="foto">Sube tu foto</label><br>
      <input id="foto" type="file" accept="image/*"><br>
      <button id="analizar" disabled>Analizar rostro y productos</button>
      <div id="resultado" class="msg" style="display:none"></div>
      <div id="productos" class="grid"></div>
    </section>
  </main>
  <script>
    const foto=document.getElementById('foto'), btn=document.getElementById('analizar'), res=document.getElementById('resultado'), productos=document.getElementById('productos');
    foto.addEventListener('change',()=>btn.disabled=!foto.files[0]);
    btn.addEventListener('click',async()=>{
      if(!foto.files[0]) return;
      const fd=new FormData(); fd.append('foto',foto.files[0]); fd.append('pais',document.getElementById('pais').value);
      res.style.display='block'; res.textContent='Analizando...'; productos.innerHTML='';
      try{
        const r=await fetch('/api/diagnostico',{method:'POST',body:fd});
        const data=await r.json();
        if(!r.ok||data.error) throw new Error(data.error||'Error del servidor');
        const detalles=[
          data.analysis_mode?'<b>Modo:</b> '+data.analysis_mode:'',
          data.confianza?'<b>Confianza:</b> '+Math.round(data.confianza*100)+'%':'',
          data.tipo_piel?'<b>Tipo de piel:</b> '+data.tipo_piel:'',
          data.subtono?'<b>Subtono:</b> '+data.subtono:'',
          data.nivel_grasa?'<b>Grasa/brillo:</b> '+data.nivel_grasa:'',
          data.nivel_hidratacion?'<b>Hidratacion:</b> '+data.nivel_hidratacion:'',
          data.textura?'<b>Textura:</b> '+data.textura:'',
          data.recomendacion?'<b>Recomendacion:</b> '+data.recomendacion:''
        ].filter(Boolean).join('<br>');
        const rutina=(data.rutina_manana||[]).length?'<br><b>Rutina manana:</b><ul>'+data.rutina_manana.map(x=>'<li>'+x+'</li>').join('')+'</ul>':'';
        res.innerHTML=detalles+rutina;
        productos.innerHTML=(data.productos||[]).map(p=>'<div class="prod"><img src="'+(p.imagen||'/assets/home.jpg')+'" alt=""><b>'+p.nombre+'</b><br><span>'+p.marca+'</span><p>'+p.desc+'</p><b>'+p.precio+'</b></div>').join('');
      }catch(e){res.innerHTML='Error en el analisis.<br><span style="color:#b91c1c">'+e.message+'</span>'}
    });
  </script>
</body>
</html>"""


def _fallback_index_html():
    return """<!doctype html>
<html lang="es">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>AMATOTY</title>
<style>body{margin:0;background:#f8fafc;font-family:Arial,sans-serif;color:#111827}.hero{max-width:900px;margin:42px auto;padding:28px 18px;text-align:center}.btn{display:inline-block;background:#d81b60;color:white;padding:14px 24px;border-radius:10px;text-decoration:none;font-weight:700}</style></head>
<body><main class="hero"><h1>AMATOTY - Oye Bonita</h1><p>Diagnostico facial y productos recomendados.</p><a class="btn" href="/oye-bonita.html">Abrir Oye Bonita</a></main></body></html>"""


def _fallback_css():
    return "body{font-family:Arial,sans-serif;background:#f8fafc;color:#1f2937}.btn{background:#d81b60;color:#fff;padding:10px 18px;border-radius:8px;text-decoration:none}.card{background:white;border-radius:12px;padding:16px}"


def _send_site_file(filename):
    normalized = filename.strip("/") or "index.html"
    if normalized == "oye-bonita":
        normalized = "oye-bonita.html"
    if normalized.lower().startswith("productos/"):
        product_file = normalized.split("/", 1)[1]
        # Check workspace root Productos/ first (local), then backend/docs/Productos/ (Render)
        for products_dir in [_data_path("Productos"), os.path.join(LOCAL_SITE_DIR, "Productos")]:
            product_path = os.path.abspath(os.path.join(products_dir, product_file))
            if product_path.startswith(os.path.abspath(products_dir)) and os.path.exists(product_path):
                return send_from_directory(products_dir, product_file)
    site_dirs = [LOCAL_SITE_DIR, SITE_DIR] if normalized == "product-platform.html" else [SITE_DIR, LOCAL_SITE_DIR]
    for site_dir in site_dirs:
        path = os.path.abspath(os.path.join(site_dir, normalized))
        if path.startswith(os.path.abspath(site_dir)) and os.path.exists(path):
            return send_from_directory(site_dir, normalized)
    if normalized in ["index.html", ""]:
        return _fallback_index_html()
    if normalized in ["oye-bonita.html", "oye_bonita.html"]:
        return _fallback_oye_bonita_html()
    if normalized == "assets/style.css":
        return _fallback_css(), 200, {"Content-Type": "text/css; charset=utf-8"}
    return jsonify({"error": "Archivo no encontrado", "path": normalized}), 404


def _init_tracking_db():
    os.makedirs(os.path.dirname(TRACKING_DB_PATH), exist_ok=True)
    with sqlite3.connect(TRACKING_DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tracking_events (
                id TEXT PRIMARY KEY,
                product_name TEXT,
                source TEXT,
                event_type TEXT,
                page_url TEXT,
                referrer TEXT,
                user_agent TEXT,
                created_at TEXT
            )
            """
        )


def _load_beauty_products():
    candidates = [
        os.environ.get("BEAUTY_PRODUCTS_PATH"),
        _data_path("docs", "assets", "beauty_products.json"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "docs", "assets", "beauty_products.json")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "beauty_products.json")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "beauty_products.json")),
    ]
    for products_path in candidates:
        if products_path and os.path.exists(products_path):
            with open(products_path, encoding="utf-8") as f:
                return json.load(f)
    return [
        {
            "id": "rutina-basica",
            "nombre": "Rutina basica de cuidado facial",
            "marca": "Oye Bonita",
            "categoria": "Belleza",
            "beneficios": ["Limpieza", "Hidratacion", "Proteccion diaria"],
            "resultados_esperados": "Rutina inicial para mantener la piel limpia e hidratada.",
            "modo_uso": "Usar manana y noche segun necesidad.",
            "tipo_piel_recomendado": "Todo tipo de piel",
            "precio": 0,
            "stock": 1,
            "imagen_ref": "assets/placeholder.png",
        }
    ]


def _extract_json(text):
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        raw = raw[start : end + 1]
    return json.loads(raw)


def _analizar_imagen_con_gemini(image_bytes, mime_type, pais):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None

    try:
        from google import genai
        from google.genai import types
    except Exception as exc:
        raise RuntimeError(
            "Falta instalar google-genai para usar Gemini."
        ) from exc

    client = genai.Client(api_key=api_key)
    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type or "image/jpeg",
    )
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            image_part,
            f"Pais del usuario: {pais}. {GEMINI_DIAGNOSTICO_PROMPT}",
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.35,
        ),
    )
    return _extract_json(response.text)


def _productos_personalizados(productos, diagnostico_ai):
    if not diagnostico_ai:
        return productos

    texto = " ".join(
        [
            str(diagnostico_ai.get("tipo_piel", "")),
            str(diagnostico_ai.get("subtono", "")),
            str(diagnostico_ai.get("nivel_grasa", "")),
            str(diagnostico_ai.get("nivel_hidratacion", "")),
            str(diagnostico_ai.get("textura", "")),
            str(diagnostico_ai.get("manchas_o_tono", "")),
            " ".join(diagnostico_ai.get("ingredientes_recomendados") or []),
        ]
    ).lower()
    prioridades = [
        ("grasa", ["mate", "polvo", "sellado", "oil", "brillo"]),
        ("mixta", ["base", "mate", "hidrat", "sellado"]),
        ("seca", ["hidrat", "glow", "crema", "luminos"]),
        ("sensible", ["suave", "calm", "sin fragancia", "sensible"]),
        ("mancha", ["tono", "proteccion", "vitamina", "uniform"]),
        ("labios", ["labial", "lip", "balsamo"]),
    ]

    def score(prod):
        base = 0
        blob = " ".join(
            [
                str(prod.get("nombre", "")),
                str(prod.get("marca", "")),
                str(prod.get("categoria", "")),
                str(prod.get("desc", "")),
                " ".join(prod.get("beneficios") or []),
            ]
        ).lower()
        for condition, keywords in prioridades:
            if condition in texto:
                base += sum(2 for keyword in keywords if keyword in blob)
        if int(prod.get("stock") or 0) > 0:
            base += 1
        return base

    ranked = sorted(productos, key=score, reverse=True)
    for idx, prod in enumerate(ranked, start=1):
        prod["destacado"] = idx <= 3
    return ranked


def _detectar_rostro(img):
    try:
        import mediapipe as mp
        import numpy as np

        img_rgb = img.convert("RGB")
        with mp.solutions.face_detection.FaceDetection(
            model_selection=1,
            min_detection_confidence=0.5,
        ) as face_detection:
            results = face_detection.process(np.array(img_rgb))
        return bool(results.detections)
    except Exception:
        # El diagnostico no debe romperse si Render no logra cargar mediapipe.
        return True


def _productos_belleza(simbolo):
    beauty_products = _load_beauty_products()

    productos = []
    for idx, prod in enumerate(beauty_products, start=1):
        beneficios = prod.get("beneficios") or []
        desc = prod.get("resultados_esperados") or ", ".join(beneficios)
        precio = float(prod.get("precio") or 0)
        stock = int(prod.get("stock") or 0)
        productos.append(
            {
                "id": prod.get("id") or f"beauty-{idx}",
                "nombre": prod.get("nombre", "Producto recomendado"),
                "marca": prod.get("marca", ""),
                "categoria": prod.get("categoria", ""),
                "desc": desc,
                "beneficios": beneficios,
                "modo_uso": prod.get("modo_uso", ""),
                "tipo_piel_recomendado": prod.get("tipo_piel_recomendado", ""),
                "precio": f"{simbolo} {precio:.2f}",
                "precio_numero": precio,
                "stock": stock,
                "imagen": prod.get("imagen_ref", ""),
            }
        )
    return productos


def _leer_precio(precio):
    match = re.search(r"(\d+(?:[.,]\d+)?)", str(precio or ""))
    return float(match.group(1).replace(",", ".")) if match else 0.0


@app.route("/")
def home():
    return _send_site_file("index.html")


@app.route("/oye_bonita.html")
def oye_bonita_underscore():
    return _send_site_file("oye-bonita.html")


@app.route("/health")
@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "lca-pro"}), 200


@app.route("/track", methods=["POST"])
def track():
    data = request.get_json(silent=True) or {}
    try:
        _init_tracking_db()
        with sqlite3.connect(TRACKING_DB_PATH) as conn:
            conn.execute(
                """
                INSERT INTO tracking_events (
                    id, product_name, source, event_type, page_url,
                    referrer, user_agent, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    data.get("product_name", ""),
                    data.get("source", ""),
                    data.get("event_type", ""),
                    data.get("page_url", ""),
                    data.get("referrer", ""),
                    request.headers.get("User-Agent", ""),
                    datetime.utcnow().isoformat(),
                ),
            )
    except Exception as exc:
        return jsonify({"ok": False, "error": f"No se pudo guardar tracking: {exc}"}), 500
    return jsonify({"ok": True}), 200


@app.route("/analisis", methods=["POST"])
def analisis():
    if "imagen" not in request.files:
        return jsonify({"error": "No hay imagen"}), 400
    return jsonify({"ok": True})


@app.route("/api/image-rules", methods=["GET"])
def image_rules():
    return jsonify(
        {
            "image_min_score": IMAGE_MIN_SCORE,
            "publish_rule": (
                "Publicar una imagen solo si image_verified=true y "
                "image_match_score>=0.82."
            ),
            "validation_prompt": IMAGE_VALIDATION_PROMPT,
        }
    )


@app.route("/api/universal-product-schema", methods=["GET"])
def universal_product_schema():
    return jsonify(
        {
            "mode": "universal_multicategory",
            "prompt": UNIVERSAL_VISUAL_AGENT_PROMPT,
            "schema": {
                "deteccion_universal": {
                    "version": "2026-05-01-universal",
                    "idioma": "es",
                    "resumen_escena": "Descripcion breve de la escena y cantidad de productos detectados",
                    "productos": [
                        {
                            "id_temporal": "prod_1",
                            "categoria_maestra": "Tecnologia / Hogar / Construccion / Moda / Belleza / Cocina / Automocion / Otro",
                            "industria_detectada": "Industria inferida automaticamente",
                            "producto_principal": {
                                "nombre_generico": "Nombre comun del objeto",
                                "marca": "Nombre de la marca o Desconocida",
                                "modelo": "Codigo/modelo detectado por OCR o Desconocido",
                                "descripcion_visual": "Colores, formas, logos, empaque, estado y elementos visibles",
                                "estado": "nuevo / usado / reacondicionado / desconocido",
                                "nivel_confianza": 0.0,
                            },
                            "ocr": {
                                "texto_detectado": [],
                                "posibles_modelos": [],
                                "posibles_especificaciones": [],
                            },
                            "especificaciones_dinamicas": [
                                {"etiqueta": "Material/Capacidad/Conectividad", "valor": "Valor detectado"}
                            ],
                            "panel_de_ventas": {
                                "mejor_opcion_argumento": "Propuesta de valor honesta",
                                "beneficio_principal": "Ahorro / durabilidad / estatus / practicidad / rendimiento",
                                "etiquetas_busqueda": [],
                                "recomendacion_cross_selling": "Producto complementario",
                                "riesgos_o_validaciones": [],
                            },
                            "publicacion": {
                                "titulo_seo": "Titulo listo para ecommerce",
                                "descripcion_corta": "Descripcion comercial breve",
                                "search_query": "consulta marketplace",
                                "image_must_show": [],
                                "image_must_not_show": [],
                                "image_verified": False,
                                "image_match_score": 0.0,
                            },
                        }
                    ],
                }
            },
        }
    )


@app.route("/api/catalogo-belleza", methods=["GET"])
def catalogo_belleza():
    pais = request.args.get("pais", "PE").upper()
    simbolo, _factor = MONEDAS.get(pais, MONEDAS["OTRO"])
    productos = _productos_belleza(simbolo)
    return jsonify(
        {
            "catalog_version": "2026-05-01-8-productos",
            "total_productos": len(productos),
            "productos": productos,
        }
    )


def _load_trending_products():
    candidates = [
        _data_path("docs", "assets", "trending_products.json"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "docs", "assets", "trending_products.json")),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "assets", "trending_products.json")),
    ]
    for products_path in candidates:
        if products_path and os.path.exists(products_path):
            with open(products_path, encoding="utf-8") as f:
                payload = json.load(f)
            return payload.get("products") or []
    return []


SMART_SEARCH_PROMPT = """
Eres un asesor, analista e inspector comercial visual y auditivo tipo Google
Shopping / Alibaba, pero mas especifico porque analizas evidencias de imagen o
audio y produces opciones comprables con ficha tecnica.

Debes:
- Si es imagen: inspeccionar pixel por pixel a nivel visual, detectar objetos,
  OCR, marcas, modelo, medidas, materiales, color, conectores, empaque, estado
  visible, compatibilidad, eje/posicion de uso cuando aplique y contexto.
- Si es audio: transcribir la intencion, detectar producto, marca, modelo,
  especificaciones mencionadas y necesidad de compra.
- No procesar ni describir contenido sexual, desnudez, explotación, violencia
  grafica o solicitudes indecentes. Si aparece, responde blocked=true.
- No inventes una imagen externa ni URL falsa.
- Para cada producto detectado, devuelve minimo 10 opciones comprables cuando
  haya intencion de compra. Deben estar ordenadas por price_sale de menor a
  mayor e incluir marcas/fabricantes y opciones genericas cuando no exista
  modelo exacto.
- Usa imagen solo si viene de marketplace, fabricante o fuente verificable.
  Si no puedes verificarla, deja image vacio e image_verified=false.
- Prioriza fuentes autorizadas: Amazon, AliExpress y Mercado Libre. Si no hay
  coincidencia suficiente, recomienda consultar fabricante oficial de la marca
  detectada o alternativas reconocidas del sector.
- Para neumaticos identifica tipo de vehiculo, medida, aro/rin, perfil, ancho,
  indice de carga, indice de velocidad, labrado, posicion recomendada
  delantera/trasera/eje de traccion cuando sea inferible, marca visible,
  compatibilidades y ficha tecnica.
- Actua por pais: adapta moneda, texto comercial, marketplace probable y cultura.
- Calcula precio_venta aplicando el margen indicado sobre precio_base.
- Devuelve SOLO JSON valido.

Schema:
{
  "blocked": false,
  "block_reason": "",
  "analysis_mode": "image|audio",
  "country": "codigo pais",
  "currency": "moneda",
  "marketplace_hint": "Amazon/MercadoLibre/AliExpress/Alibaba/local",
  "evidence": {
    "summary": "resumen de evidencia",
    "detected_text": [],
    "visual_or_audio_clues": [],
    "uncertainties": []
  },
  "products": [
    {
      "name": "nombre comercial buscable",
      "brand": "marca o Generic",
      "category": "categoria",
      "product_type": "tipo exacto",
      "problem": "problema que resuelve",
      "target": "publico objetivo",
      "short_desc": "descripcion comercial",
      "reason": "argumento comercial honesto",
      "hook": "gancho breve",
      "specs": "Capacidad: ..., Material: ..., Uso: ...",
      "model": "modelo/referencia si existe",
      "sector": "hogar|belleza|mecanica|industrial|medicina|construccion|tecnologia|seguridad|automotriz|otros",
      "material": "material principal si se detecta",
      "compatibility": "medidas, modelos, normas o equipos compatibles",
      "provider": "proveedor o marketplace autorizado sugerido",
      "source_links": [{"name": "Amazon", "url": "https://...", "type": "marketplace"}],
      "stock": 0,
      "warranty": "garantia esperada o pendiente de validar",
      "rating": 4.2,
      "quality": "professional|premium|economy",
      "pros": ["ventaja tecnica 1", "ventaja comercial 2"],
      "cons": ["validacion pendiente 1", "limitacion 2"],
      "similar_products": ["alternativa comparable 1"],
      "search_query": "consulta precisa para marketplace del pais",
      "price_base": 0,
      "price_sale": 0,
      "currency": "moneda",
      "image_verified": false,
      "image_match_score": 0.0
    }
  ]
}
"""


def _market_context(country, currency):
    country = (country or "US").upper()
    defaults = {
        "US": ("USD", "Amazon US", "cart", "businesslike, direct and review-driven"),
        "PE": ("PEN", "MercadoLibre Peru", "carrito", "practico, ahorro y confianza"),
        "CO": ("COP", "MercadoLibre Colombia", "canasta", "cercano, claro y orientado a beneficio"),
        "MX": ("MXN", "MercadoLibre Mexico", "carrito", "directo, comparativo y promocional"),
        "CL": ("CLP", "MercadoLibre Chile", "carrito", "sobrio, tecnico y precio claro"),
        "AR": ("ARS", "MercadoLibre Argentina", "carrito", "comparativo, precio y disponibilidad"),
        "EC": ("USD", "MercadoLibre Ecuador", "carrito", "simple, confiable y practico"),
        "BO": ("BOB", "marketplace Bolivia", "carrito", "practico y precio claro"),
        "PY": ("PYG", "marketplace Paraguay", "carrito", "directo y orientado a utilidad"),
        "UY": ("UYU", "MercadoLibre Uruguay", "carrito", "sobrio y confiable"),
        "BR": ("BRL", "Mercado Livre Brasil", "carrinho", "portugues comercial claro"),
        "VE": ("USD", "marketplace Venezuela", "carrito", "precio claro y disponibilidad"),
    }
    default_currency, marketplace, cart_word, tone = defaults.get(country, defaults["US"])
    return {
        "country": country,
        "currency": currency or default_currency,
        "marketplace": marketplace,
        "cart_word": cart_word,
        "tone": tone,
    }


def _clean_link_query(item):
    name = _clean_search_text(item.get("link_query") or item.get("name") or "")
    query = _plain_text(name or _clean_search_text(item.get("search_query") or ""))
    query = re.sub(
        r"\b(precio|price|amazon\s*us|amazon|mercadolibre|mercado\s+libre|aliexpress|ficha\s+tecnica|ficha\s+t[eé]cnica)\b",
        " ",
        query,
        flags=re.I,
    )
    query = re.sub(r"\s+", " ", query).strip()
    return query or "producto"


def _official_brand_source(brand, product_name=""):
    brand = (brand or "").lower()
    if not brand or brand.startswith("generic") or brand in {"por validar"}:
        return None
    brand_tokens = set(re.findall(r"[a-z0-9]+", brand))
    long_brands = [
        "samsung",
        "whirlpool",
        "midea",
        "bosch",
        "electrolux",
        "maytag",
        "michelin",
        "goodyear",
        "bridgestone",
        "pirelli",
        "continental",
    ]
    is_short_brand = "lg" in brand_tokens or "ge" in brand_tokens
    if not is_short_brand and not any(token in brand for token in long_brands):
        return None
    query = urllib.parse.quote_plus(_clean_search_text(f"{product_name} {brand} oficial"))
    return {"name": "Buscar oficial", "url": f"https://www.google.com/search?q={query}", "type": "official_search"}


def _provider_source_links(item):
    query = urllib.parse.quote_plus(_clean_link_query(item))
    links = [
        {"name": "Amazon", "url": f"https://www.amazon.com/s?k={query}", "type": "marketplace"},
        {"name": "AliExpress", "url": f"https://www.aliexpress.com/wholesale?SearchText={query}", "type": "marketplace"},
        {"name": "Mercado Libre", "url": f"https://listado.mercadolibre.com/{query}", "type": "marketplace"},
    ]
    official = _official_brand_source(item.get("brand"), item.get("name"))
    if official:
        links.append(official)
    return links


def _mercadolibre_site(country):
    return {
        "AR": "MLA",
        "BO": "MBO",
        "BR": "MLB",
        "CL": "MLC",
        "CO": "MCO",
        "EC": "MEC",
        "MX": "MLM",
        "PE": "MPE",
        "PY": "MPY",
        "UY": "MLU",
        "VE": "MLV",
    }.get((country or "US").upper(), "MLM")


def _plain_text(value):
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.lower()


def _clean_search_text(value):
    text = str(value or "").strip()
    text = re.sub(r"\.[a-z0-9]{2,5}$", "", text, flags=re.I)
    text = re.sub(r"[_-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _tokens(value):
    stop = {
        "de",
        "del",
        "la",
        "el",
        "para",
        "con",
        "sin",
        "foto",
        "image",
        "img",
        "producto",
        "precio",
    }
    return set(re.findall(r"[a-z0-9]+", _plain_text(value))) - stop


def _infer_product_family(value):
    haystack = _plain_text(value)
    for family in SHOPPING_FAMILIES:
        if any(term in haystack for term in family["terms"]):
            return family
    return None


def _market_match_score(query, title):
    query_tokens = _tokens(query)
    title_tokens = _tokens(title)
    if not query_tokens:
        return 0.5
    overlap = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
    family = _infer_product_family(query)
    if family and any(term in _plain_text(title) for term in family["terms"]):
        overlap += 0.25
    return min(overlap, 0.96)


def _to_usd_amount(amount, currency):
    try:
        value = float(amount or 0)
    except (TypeError, ValueError):
        value = 0
    factor = FX_TO_USD.get(str(currency or "USD").upper(), 1.0)
    return round(value * factor, 2)


def _secure_image_url(url):
    url = str(url or "").strip()
    if url.startswith("http://"):
        url = "https://" + url[7:]
    return url


def _is_web_image_url(url):
    url = str(url or "").strip().lower()
    return url.startswith("https://") or url.startswith("http://")


def _serpapi_key():
    return (
        os.environ.get("SERPAPI_KEY")
        or os.environ.get("SERP_API_KEY")
        or os.environ.get("SERPAPI_API_KEY")
        or ""
    ).strip()


def _serpapi_image_lookup_limit():
    try:
        return max(0, int(os.environ.get("SERPAPI_IMAGE_LOOKUPS", "10")))
    except (TypeError, ValueError):
        return 10


def _serpapi_image_for_query(query):
    api_key = _serpapi_key()
    query = _clean_search_text(query)
    if not api_key or not query:
        return ""
    params = urllib.parse.urlencode(
        {
            "engine": "google_images",
            "q": query,
            "api_key": api_key,
            "ijn": "0",
        }
    )
    url = f"https://serpapi.com/search.json?{params}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AMATOTY-Product-Advisor/1.0"})
        with urllib.request.urlopen(req, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return ""

    blocked = ("placeholder", "source.unsplash.com", "picsum.photos")
    for result in payload.get("images_results", []) or []:
        for field in ("original", "thumbnail"):
            image_url = _secure_image_url(result.get(field) or "")
            lowered = image_url.lower()
            if _is_web_image_url(image_url) and not any(item in lowered for item in blocked):
                return image_url
    return ""


def _product_image_query(product, fallback_query=""):
    for value in [
        product.get("link_query"),
        product.get("search_query"),
        " ".join([str(product.get("brand", "")), str(product.get("name", ""))]),
        product.get("name"),
        product.get("product_type"),
        fallback_query,
    ]:
        clean = _clean_search_text(value)
        if clean:
            return clean
    return ""


def _enrich_products_with_serpapi_images(products, fallback_query=""):
        if not products:
            return products
        max_lookups = _serpapi_image_lookup_limit()
        cache = {}
        lookups = 0
        enriched = []
        for product in products:
            item = dict(product)
            current_image = _secure_image_url(item.get("image") or "")
            if _is_web_image_url(current_image):
                item["image"] = current_image
                item["image_source"] = item.get("image_source") or "web"
                enriched.append(item)
                continue
            query = _product_image_query(item, fallback_query)
            image_url = ""
            # Solo SerpApi
            if _serpapi_key() and query and lookups < max_lookups:
                if query not in cache:
                    cache[query] = _serpapi_image_for_query(query)
                    lookups += 1
                image_url = cache.get(query) or ""
                if image_url:
                    item["image"] = image_url
                    item["image_source"] = "serpapi_google_images"
                    item["image_verified"] = True
                    try:
                        item["image_match_score"] = max(float(item.get("image_match_score") or 0), 0.82)
                    except (TypeError, ValueError):
                        item["image_match_score"] = 0.82
            enriched.append(item)
        return enriched


def _ml_attribute(result, *keys):
    wanted = {_plain_text(key) for key in keys}
    for attr in result.get("attributes") or []:
        attr_keys = {
            _plain_text(attr.get("id")),
            _plain_text(attr.get("name")),
        }
        if wanted & attr_keys:
            return attr.get("value_name") or attr.get("value_id") or ""
    return ""


def _guess_brand(title):
    known = [
        "Samsung",
        "LG",
        "Whirlpool",
        "Midea",
        "Bosch",
        "Electrolux",
        "GE",
        "Maytag",
        "Hisense",
        "Haier",
        "Sony",
        "Apple",
        "Lenovo",
        "HP",
        "Dell",
        "Xiaomi",
        "Oster",
        "Black+Decker",
        "Philips",
        "Michelin",
        "Goodyear",
        "Bridgestone",
        "Pirelli",
        "Continental",
    ]
    plain_title = _plain_text(title)
    for brand in known:
        if _plain_text(brand) in plain_title:
            return brand
    return "Por validar"


def _family_source_fields(query, title=""):
    family = _infer_product_family(f"{query} {title}")
    if not family:
        return {
            "category": "marketplace",
            "product_type": "resultado marketplace",
            "sector": "comercio",
            "problem": "comparar opciones actuales, precio y disponibilidad",
            "target": "comprador que necesita cotizar opciones reales",
            "material": "",
            "compatibility": "validar modelo, medidas y garantia",
        }
    return {
        "category": family["category"],
        "product_type": family["product_type"],
        "sector": family["sector"],
        "problem": family["problem"],
        "target": family["target"],
        "material": family["material"],
        "compatibility": family["compatibility"],
    }


def _sort_smart_products(products):
    def key(item):
        try:
            price = float(item.get("price_sale") or item.get("price_base") or 0)
        except (TypeError, ValueError):
            price = 0
        try:
            score = float(item.get("image_match_score") or item.get("confidence") or 0)
        except (TypeError, ValueError):
            score = 0
        return (price <= 0, price, -score, str(item.get("name", "")))

    return sorted(products or [], key=key)


def _catalog_template_products(query, context, margin, count=SMART_MIN_OPTIONS):
    clean_query = _clean_search_text(query) or "producto comercial"
    family = _infer_product_family(clean_query)
    marketplace = context["marketplace"]
    products = []

    if family:
        for name, brand, price, specs, quality in family["templates"][:count]:
            fields = _family_source_fields(clean_query, name)
            products.append(
                {
                    "name": name,
                    "brand": brand,
                    **fields,
                    "short_desc": f"Opcion {quality} para comparar {family['product_type']} por precio, capacidad y garantia.",
                    "reason": "Opcion comercial sugerida para completar la comparacion cuando no hay suficientes resultados vivos.",
                    "hook": "Validar capacidad, consumo, garantia y entrega antes de comprar.",
                    "specs": specs,
                    "model": "",
                    "provider": marketplace,
                    "supplier": "Proveedor por validar",
                    "stock": 0,
                    "warranty": "Validar con vendedor",
                    "rating": 4.2,
                    "quality": quality,
                    "search_query": name,
                    "link_query": name,
                    "price_base": price,
                    "image": "",
                    "image_verified": False,
                    "image_match_score": 0,
                }
            )
    else:
        tiers = [
            ("economica", "Generic", 0.55, "economy"),
            ("compacta", "Generic", 0.75, "economy"),
            ("estandar", "Generic", 1.0, "professional"),
            ("profesional", "Generic Pro", 1.35, "professional"),
            ("alta capacidad", "Generic Pro", 1.7, "professional"),
            ("premium", "Premium Choice", 2.2, "premium"),
            ("industrial ligera", "Industrial Choice", 2.8, "professional"),
            ("industrial premium", "Industrial Choice", 3.5, "premium"),
            ("smart", "Smart Choice", 4.2, "premium"),
            ("enterprise", "Enterprise Choice", 5.0, "premium"),
        ]
        for idx, (suffix, brand, multiplier, quality) in enumerate(tiers[:count], start=1):
            base = round(50 * multiplier, 2)
            products.append(
                {
                    "name": f"{clean_query.title()} {suffix}",
                    "brand": brand,
                    "category": "comercio",
                    "product_type": clean_query,
                    "sector": "comercio",
                    "short_desc": "Opcion generada para comparar proveedores, ficha tecnica y precio.",
                    "problem": "identificar alternativas comprables para una busqueda amplia",
                    "target": "compradores, reventa, mantenimiento y usuarios finales",
                    "reason": "Sirve como consulta precisa cuando la evidencia no alcanza para un modelo exacto.",
                    "hook": "Compara precio, garantia, ficha tecnica y devolucion.",
                    "specs": f"Uso: comercial, Nivel: {suffix}, Validar: marca/modelo/compatibilidad",
                    "model": "",
                    "material": "",
                    "compatibility": "validar ficha tecnica",
                    "provider": marketplace,
                    "supplier": "Proveedor por validar",
                    "stock": 0,
                    "warranty": "Validar con vendedor",
                    "rating": 4.0,
                    "quality": quality,
                    "search_query": clean_query,
                    "link_query": clean_query,
                    "price_base": base,
                    "image": "",
                    "image_verified": False,
                    "image_match_score": 0,
                }
            )

    return _normalize_smart_products(products, context["currency"], margin)


def _candidate_queries(query, products):
    candidates = []
    for value in [query]:
        clean = _clean_search_text(value)
        if clean:
            candidates.append(clean)
    for item in products or []:
        for value in [
            item.get("link_query"),
            item.get("search_query"),
            " ".join([str(item.get("brand", "")), str(item.get("name", ""))]),
            item.get("product_type"),
        ]:
            clean = _clean_search_text(value)
            if clean and clean not in candidates:
                candidates.append(clean)
    return candidates[:4]


def _ensure_minimum_options(products, query, context, margin, min_count=SMART_MIN_OPTIONS):
    merged = _merge_product_lists(products)
    # Si min_count es 0, no forzar mínimo ni agregar plantillas
    if not query or min_count == 0 or len(merged) >= min_count:
        return _sort_smart_products(merged)

    for candidate in _candidate_queries(query, merged):
        if len(merged) >= min_count:
            break
        live = _search_mercadolibre_products(
            candidate,
            context,
            margin,
            limit=max(SMART_LIVE_SEARCH_LIMIT, min_count - len(merged)),
        )
        merged = _merge_product_lists(merged, live)

    if min_count > 0 and len(merged) < min_count:
        templates = _catalog_template_products(query, context, margin, count=min_count)
        merged = _merge_product_lists(merged, templates)

    return _sort_smart_products(merged)[: max(len(merged), min_count)]


def _search_mercadolibre_products(query, context, margin, limit=SMART_LIVE_SEARCH_LIMIT):
    if not query:
        return []
    query = _clean_search_text(query)
    site = _mercadolibre_site(context.get("country"))
    url = (
        f"https://api.mercadolibre.com/sites/{site}/search?"
        f"q={urllib.parse.quote_plus(query)}&limit={int(limit)}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AMATOTY-Product-Advisor/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        return []

    products = []
    for result in payload.get("results", [])[:limit]:
        title = result.get("title") or "Producto Mercado Libre"
        relevance = _market_match_score(query, title)
        if relevance < 0.24:
            continue
        source_currency = result.get("currency_id") or context.get("currency")
        price = float(result.get("price") or 0) or 10
        price_usd = _to_usd_amount(price, source_currency)
        seller = result.get("seller") or {}
        permalink = result.get("permalink") or ""
        brand = _ml_attribute(result, "BRAND", "Marca") or _guess_brand(title)
        model = _ml_attribute(result, "MODEL", "Modelo")
        line = _ml_attribute(result, "LINE", "Linea")
        fields = _family_source_fields(query, title)
        condition = result.get("condition") or "validar"
        sold = result.get("sold_quantity", 0)
        thumbnail = _secure_image_url(result.get("secure_thumbnail") or result.get("thumbnail") or "")
        score = round(max(0.82, min(0.96, relevance)), 2) if thumbnail else round(relevance, 2)
        spec_parts = [
            f"Condicion: {condition}",
            f"Vendidos: {sold}",
            f"Precio fuente: {source_currency} {price:.2f}",
        ]
        if model:
            spec_parts.append(f"Modelo: {model}")
        if line:
            spec_parts.append(f"Linea: {line}")
        item = {
            "name": title,
            "brand": brand,
            **fields,
            "short_desc": "Resultado encontrado en Mercado Libre mediante API publica autorizada.",
            "reason": "Coincidencia comercial real; validar ficha, vendedor, garantia y compatibilidad.",
            "hook": "Precio y enlace disponibles para revision inmediata.",
            "specs": ", ".join(spec_parts),
            "model": model,
            "search_query": query,
            "link_query": title,
            "price_base": price_usd,
            "price_sale": round(price_usd * (1 + margin / 100), 2),
            "currency": context.get("currency"),
            "original_price": price,
            "original_currency": source_currency,
            "provider": "Mercado Libre",
            "supplier": seller.get("nickname") or "Vendedor Mercado Libre",
            "stock": int(result.get("available_quantity") or 0),
            "warranty": "Validar en publicacion",
            "rating": 4.2,
            "quality": "professional",
            "image": thumbnail,
            "image_source": "marketplace_thumbnail",
            "image_verified": bool(thumbnail),
            "image_match_score": score,
            "source_links": [
                {"name": "Mercado Libre", "url": permalink, "type": "marketplace"},
                *_provider_source_links({"name": title, "search_query": query, "brand": ""})[:2],
            ],
        }
        products.append(item)
    return _normalize_smart_products(products, context.get("currency"), margin)


def _merge_product_lists(*lists):
    merged = []
    seen = set()
    for product_list in lists:
        for item in product_list or []:
            key = "|".join(
                [
                    str(item.get("name", "")),
                    str(item.get("provider", "")),
                    str(item.get("price_base", "")),
                ]
            ).lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return _sort_smart_products(merged)


def _normalize_search_query(q):
    """Normaliza una query de búsqueda: elimina acentos y aplica equivalencias
    fonéticas español/quechua (inka→inca, kola→cola, etc.)."""
    import unicodedata
    q = str(q or "").strip()
    q = unicodedata.normalize("NFD", q)
    q = "".join(c for c in q if unicodedata.category(c) != "Mn")  # eliminar diacríticos
    q = q.lower()
    q = q.replace("qu", "c").replace("k", "c")  # inka→inca, queso→ceso
    return q


def _load_platform_products(query="", category=""):
    """Lee los productos publicados de la BD del platform y los convierte al
    formato estándar que usa smart-search."""
    try:
        from product_platform import get_db, public_product_payload, product_media
        conn = get_db()
        try:
            clauses = ["p.status = 'published'", "o.status = 'active'"]
            params = []
            if query:
                # Normalizar query: eliminar acentos, k→c (inka→inca)
                q_norm = _normalize_search_query(query)
                q_like = f"%{q_norm}%"
                q_orig = f"%{query.lower()}%"
                # Buscar tanto con el query original como con el normalizado
                clauses.append("""(
                    LOWER(p.name) LIKE ? OR LOWER(p.name) LIKE ?
                    OR LOWER(p.description) LIKE ? OR LOWER(p.description) LIKE ?
                    OR LOWER(p.category) LIKE ? OR LOWER(p.category) LIKE ?
                )""")
                params.extend([q_orig, q_like, q_orig, q_like, q_orig, q_like])
            if category:
                clauses.append("LOWER(p.category) = ?")
                params.append(category.lower())
            rows = conn.execute(
                f"""
                SELECT p.*, o.name AS organization_name
                FROM platform_products p
                JOIN platform_organizations o ON o.id = p.organization_id
                WHERE {' AND '.join(clauses)}
                ORDER BY p.priority ASC, p.updated_at DESC
                LIMIT 200
                """,
                params,
            ).fetchall()
            result = []
            for row in rows:
                org = conn.execute(
                    "SELECT * FROM platform_organizations WHERE id = ?",
                    (row["organization_id"],),
                ).fetchone()
                media = product_media(conn, row["id"])
                payload = public_product_payload(row, media, org)
                # Mapear al formato esperado por smart-search
                price = float(row["price"] or 10)
                result.append({
                    "name":        row["name"],
                    "brand":       payload.get("brand") or row["organization_name"] or "",
                    "category":    row["category"] or "",
                    "description": row["description"] or "",
                    "short_desc":  (row["description"] or "")[:120],
                    "price_base":  price,
                    "price_sale":  price,
                    "currency":    row["currency"] or "USD",
                    "stock":       row["stock"] or 0,
                    "image":       payload.get("image") or "",
                    "source_links": payload.get("source_links") or [],
                    "confidence":  0.90,
                    "provider":    row["organization_name"] or "",
                    "sku":         row["sku"] or "",
                    "id":          row["id"],
                    "_source":     "platform_db",
                })
            return result
        finally:
            conn.close()
    except Exception as exc:
        import sys
        print(f"[smart-search] No se pudo leer platform_products: {exc}", file=sys.stderr)
        return []


def _smart_search_fallback(query, category, currency, margin):
    # 1. Productos de la BD del platform (guardados por el usuario)
    platform = _load_platform_products(query=query, category=category)
    # 2. Catálogo base (trending_products.json)
    trending = _load_trending_products()
    query_l   = _normalize_search_query(query)   # normalizado: acentos + k→c
    query_raw = (query or "").lower()
    category_l = (category or "").lower()
    if query_l or category_l:
        def _matches_trending(product):
            blob = " ".join([
                str(product.get("name", "")),
                str(product.get("brand", "")),
                str(product.get("category", "")),
                str(product.get("product_type", "")),
                str(product.get("problem", "")),
                str(product.get("target", "")),
                str(product.get("specs", "")),
                str(product.get("search_query", "")),
            ])
            blob_norm = _normalize_search_query(blob)
            blob_raw  = blob.lower()
            cat_ok    = not category_l or str(product.get("category", "")).lower() == category_l
            q_ok      = not query_l or (query_l in blob_norm) or (query_raw in blob_raw)
            return cat_ok and q_ok
        trending = [p for p in trending if _matches_trending(p)]
    # Unir: primero los de BD (tienen prioridad), luego el catálogo base
    seen = set()
    products = []
    for product in platform + trending:
        key = str(product.get("name", "")).lower().strip()
        if key and key not in seen:
            seen.add(key)
            products.append(product)
    for product in products:
        base = float(product.get("price_base") or product.get("base_price") or product.get("price") or 10)
        product["price_base"] = base
        product["price_sale"] = round(base * (1 + margin / 100), 2)
        product["currency"] = currency
    return _sort_smart_products(products)


def _extract_smart_products(payload):
    if not payload:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload.get("products"), list):
        return payload["products"]
    if isinstance(payload.get("productos"), list):
        return payload["productos"]
    universal = payload.get("deteccion_universal") or {}
    if isinstance(universal.get("productos"), list):
        products = []
        for product in universal["productos"]:
            principal = product.get("producto_principal") or {}
            sales = product.get("panel_de_ventas") or {}
            publish = product.get("publicacion") or {}
            specs = product.get("especificaciones_dinamicas") or []
            products.append(
                {
                    **product,
                    "name": product.get("name")
                    or principal.get("nombre_generico")
                    or publish.get("titulo_seo")
                    or "Producto detectado",
                    "brand": product.get("brand") or principal.get("marca") or "Generic",
                    "category": product.get("category")
                    or product.get("categoria_maestra")
                    or product.get("industria_detectada")
                    or "Otros",
                    "short_desc": product.get("short_desc")
                    or publish.get("descripcion_corta")
                    or principal.get("descripcion_visual")
                    or "",
                    "problem": product.get("problem")
                    or sales.get("beneficio_principal")
                    or "Necesidad por confirmar",
                    "target": product.get("target") or "Comprador por validar",
                    "specs": product.get("specs")
                    or ", ".join(
                        [
                            f"{item.get('etiqueta')}: {item.get('valor')}"
                            for item in specs
                            if isinstance(item, dict)
                        ]
                    ),
                    "reason": product.get("reason")
                    or sales.get("mejor_opcion_argumento")
                    or "",
                    "hook": product.get("hook")
                    or sales.get("recomendacion_cross_selling")
                    or "",
                    "search_query": product.get("search_query")
                    or publish.get("search_query")
                    or principal.get("nombre_generico")
                    or "",
                    "image_verified": product.get("image_verified")
                    if "image_verified" in product
                    else publish.get("image_verified", False),
                    "image_match_score": product.get("image_match_score")
                    if "image_match_score" in product
                    else publish.get("image_match_score", 0),
                }
            )
        return products
    return []


def _normalize_smart_products(products, currency, margin):
    normalized = []
    for product in products or []:
        if not isinstance(product, dict):
            continue
        item = dict(product)
        base = float(
            item.get("price_base")
            or item.get("base_price")
            or item.get("precio_base")
            or item.get("precio_numero")
            or item.get("precio")
            or 10
        )
        item["price_base"] = round(base, 2)
        item["price_sale"] = round(
            float(item.get("price_sale") or item.get("precio_venta") or base * (1 + margin / 100)),
            2,
        )
        item["currency"] = item.get("currency") or currency
        item["brand"] = item.get("brand") or "Generic"
        item["category"] = item.get("category") or "Otros"
        item["product_type"] = item.get("product_type") or item["category"]
        item["model"] = item.get("model") or item.get("modelo") or ""
        item["sector"] = item.get("sector") or item["category"]
        item["material"] = item.get("material") or ""
        item["compatibility"] = item.get("compatibility") or item.get("compatibilidad") or ""
        item["provider"] = item.get("provider") or item.get("supplier") or item.get("marketplace") or "Proveedor por validar"
        item["supplier"] = item.get("supplier") or item["provider"]
        item["source_links"] = item.get("source_links") if isinstance(item.get("source_links"), list) else _provider_source_links(item)
        item["stock"] = int(float(item.get("stock") or item.get("availability_count") or 0))
        item["warranty"] = item.get("warranty") or item.get("garantia") or "Validar con proveedor"
        item["rating"] = float(item.get("rating") or item.get("calificacion") or 4.2)
        text_blob = " ".join(
            [
                str(item.get("name", "")),
                str(item.get("brand", "")),
                str(item.get("category", "")),
                str(item.get("product_type", "")),
                str(item.get("specs", "")),
                str(item.get("reason", "")),
            ]
        ).lower()
        item["quality"] = item.get("quality") or (
            "premium" if "premium" in text_blob else "economy" if "econom" in text_blob else "professional"
        )
        item["pros"] = item.get("pros") if isinstance(item.get("pros"), list) else [
            item.get("reason") or "Producto listo para comparacion tecnica.",
            item.get("hook") or "Permite comparar precio, ficha y proveedor.",
        ]
        item["cons"] = item.get("cons") if isinstance(item.get("cons"), list) else [
            "Precio, stock y garantia deben validarse con proveedor real.",
            "Ficha tecnica final depende del modelo exacto.",
        ]
        item["similar_products"] = item.get("similar_products") if isinstance(item.get("similar_products"), list) else []
        item["search_query"] = item.get("search_query") or " ".join(
            [str(item.get("name", "")), str(item.get("brand", "")), str(item.get("specs", ""))]
        ).strip()
        item["image_verified"] = bool(item.get("image_verified", False))
        item["image_match_score"] = float(item.get("image_match_score") or item.get("confidence") or 0.78)
        normalized.append(item)
    return normalized


def _generic_smart_products(query, context, margin):
    query_text = (query or "").lower()
    if _infer_product_family(query_text):
        return _catalog_template_products(query, context, margin, count=SMART_MIN_OPTIONS)

    is_tire = any(term in query_text for term in ["llanta", "neumatic", "neumático", "295", "r22", "22.5", "truck tire"])
    marketplace = context["marketplace"]
    currency = context["currency"]
    if is_tire:
        products = [
            {
                "name": "Llanta de camion 295/80 R22.5 regional",
                "brand": "Generic",
                "category": "automocion",
                "product_type": "neumatico pesado",
                "short_desc": "Neumatico radial para camion, buses o tractomula en ruta regional.",
                "problem": "reemplazo de llanta de carga con medida 295/80 R22.5",
                "target": "flotas, transporte pesado, talleres y compradores B2B",
                "reason": "Medida comercial frecuente para carga pesada; valida indice de carga, posicion y labrado antes de comprar.",
                "hook": "Comparar precio por kilometro y garantia.",
                "specs": "Medida: 295/80 R22.5, Tipo: radial tubeless, Uso: camion/carga, Posicion: direccional o traccion por validar",
                "search_query": f"295/80R22.5 truck tire radial {marketplace}",
                "price_base": 280,
                "image_verified": False,
                "image_match_score": 0.82,
            },
            {
                "name": "Michelin X Multi 295/80 R22.5",
                "brand": "Michelin",
                "category": "automocion",
                "product_type": "llanta camion premium",
                "short_desc": "Opcion premium para rendimiento, kilometraje y operacion de flota.",
                "problem": "durabilidad y estabilidad en transporte de larga distancia",
                "target": "empresas de transporte, buses y carga pesada",
                "reason": "Marca de fabricante reconocida; conviene validar ficha exacta, disponibilidad y DOT con proveedor autorizado.",
                "hook": "Alta confianza para flotas que priorizan vida util.",
                "specs": "Medida: 295/80R22.5, Segmento: premium, Uso: regional/larga distancia, Fabricante: Michelin",
                "search_query": f"Michelin 295/80R22.5 ficha tecnica precio {marketplace}",
                "price_base": 430,
                "image_verified": False,
                "image_match_score": 0.84,
            },
            {
                "name": "Goodyear KMAX / Marathon 295/80 R22.5",
                "brand": "Goodyear",
                "category": "automocion",
                "product_type": "neumatico camion",
                "short_desc": "Alternativa de fabricante para carga pesada con enfoque en kilometraje.",
                "problem": "necesidad de llanta nueva confiable para camion",
                "target": "mantenimiento de flota y talleres",
                "reason": "Busqueda recomendada cuando el comprador pide Goodyear o equivalentes en 295/80 R22.5.",
                "hook": "Buena opcion para cotizar por eje y servicio.",
                "specs": "Medida: 295/80 R22.5, Marca: Goodyear, Aplicacion: camion, Validar: indice de carga y labrado",
                "search_query": f"Goodyear 295/80R22.5 truck tire price {marketplace}",
                "price_base": 390,
                "image_verified": False,
                "image_match_score": 0.83,
            },
            {
                "name": "Bridgestone 295/80 R22.5 para carga",
                "brand": "Bridgestone",
                "category": "automocion",
                "product_type": "llanta camion",
                "short_desc": "Llanta de fabricante para servicio regional, urbano o carretera segun labrado.",
                "problem": "cotizar marca reconocida para camion pesado",
                "target": "compras tecnicas, transporte y mantenimiento",
                "reason": "Alternativa de fabricante fuerte; revisar ficha tecnica de la referencia exacta.",
                "hook": "Ideal para comparar contra Michelin y Goodyear.",
                "specs": "Medida: 295/80R22.5, Tipo: radial, Uso: carga pesada, Validar: eje y aplicacion",
                "search_query": f"Bridgestone 295/80R22.5 ficha tecnica precio {marketplace}",
                "price_base": 410,
                "image_verified": False,
                "image_match_score": 0.82,
            },
            {
                "name": "Llanta economica 295/80 R22.5 tubeless",
                "brand": "Generic",
                "category": "automocion",
                "product_type": "llanta camion economica",
                "short_desc": "Opcion generica para cotizacion rapida cuando no hay marca obligatoria.",
                "problem": "presupuesto limitado para reemplazo de neumatico pesado",
                "target": "talleres, pequenos transportadores y reventa",
                "reason": "Sirve para iniciar busqueda cuando la evidencia solo confirma medida y tipo de producto.",
                "hook": "Pedir garantia, fecha DOT y certificaciones antes de cerrar.",
                "specs": "Medida: 295/80 R22.5, Construccion: radial, Camara: tubeless, Uso: camion",
                "search_query": f"llanta 295/80R22.5 nueva precio {marketplace}",
                "price_base": 250,
                "image_verified": False,
                "image_match_score": 0.8,
            },
        ]
    else:
        clean_query = (query or "producto comercial").strip()
        products = [
            {
                "name": f"{clean_query.title()} profesional",
                "brand": "Generic",
                "category": "industria",
                "product_type": "producto tecnico",
                "short_desc": "Resultado generico listo para cotizar cuando no hay coincidencia exacta.",
                "problem": "identificar proveedores y especificaciones de compra",
                "target": "compras, mantenimiento, comercio e industria",
                "reason": "La busqueda amplia se convierte en una consulta tecnica para comparar proveedores.",
                "hook": "Validar marca, modelo, certificacion y garantia.",
                "specs": "Uso: comercial/industrial, Estado: nuevo, Validar: ficha tecnica y compatibilidad",
                "search_query": f"{clean_query} ficha tecnica precio {marketplace}",
                "price_base": 50,
                "image_verified": False,
                "image_match_score": 0.72,
            }
        ]
    normalized = _normalize_smart_products(products, currency, margin)
    if len(normalized) < SMART_MIN_OPTIONS:
        normalized = _merge_product_lists(
            normalized,
            _catalog_template_products(query, context, margin, count=SMART_MIN_OPTIONS),
        )
    return normalized


def _smart_text_with_gemini(query, category, context, margin):
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key or not query:
        return None
    try:
        from google import genai
        from google.genai import types

        prompt = f"""
Eres un motor comercial tipo Google Shopping, Alibaba y compras B2B.
Convierte una busqueda corta en productos comprables con ficha tecnica.

Entrada del usuario: {query}
Categoria elegida: {category or 'todas'}
Pais: {context['country']}
Moneda: {context['currency']}
Marketplace probable: {context['marketplace']}
Tono cultural: {context['tone']}
Margen de ganancia: {margin}%

Reglas:
- Si la busqueda es amplia, infiere el producto probable. Ejemplo: LLANTA puede ser neumatico; si hay imagen/nombre con 295 80 r 22.5, tratalo como llanta de camion 295/80 R22.5.
- Para marcas/fabricantes, usa nombres buscables y recomienda validar ficha oficial, medida, modelo, compatibilidad y garantia.
- Incluye opciones de fabricante y genericas si no hay modelo exacto.
- Devuelve minimo 10 productos comprables y ordenalos por precio_venta/price_sale ascendente.
- Cubre cualquier sector: comercio, industria, construccion, mantenimiento, medicina, automocion, tecnologia, hogar.
- No afirmes que viste ofertas en vivo. Genera consultas precisas para encontrar ofertas actuales.
- Devuelve SOLO JSON valido con el mismo schema de SMART_SEARCH_PROMPT.

{SMART_SEARCH_PROMPT}
"""
        response = genai.Client(api_key=api_key).models.generate_content(
            model=GEMINI_MODEL,
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        return _extract_json(response.text)
    except Exception as exc:
        return {"error": str(exc)}


@app.route("/api/smart-search", methods=["POST"])
def smart_search():
    data = request.get_json(silent=True) or {}
    query_raw = str(data.get("query") or "").strip()
    query = query_raw.lower()
    category = str(data.get("category") or "").strip().lower()
    currency = str(data.get("currency") or "USD").upper()
    margin = float(data.get("margin") or 20)
    country = data.get("country", "US")
    context = _market_context(country, currency)

    products = _smart_search_fallback(query, category, currency, margin)
    analysis_mode = "smart_search_catalog"
    evidence = {
        "summary": f"Catalogo local filtrado por: {query_raw or 'todos'}",
        "detected_text": [query_raw] if query_raw else [],
        "visual_or_audio_clues": [],
        "uncertainties": [],
    }

    if not products and query_raw:
        ai_payload = _smart_text_with_gemini(query_raw, category, context, margin)
        ai_products = _extract_smart_products(ai_payload or {})
        if ai_products:
            products = _normalize_smart_products(ai_products, context["currency"], margin)
            analysis_mode = "gemini_text_search"
            evidence = (ai_payload or {}).get("evidence") or {
                "summary": f"Busqueda IA generada para {query_raw}",
                "detected_text": [query_raw],
                "visual_or_audio_clues": ["consulta textual"],
                "uncertainties": ["Valida disponibilidad y precio final en el marketplace."],
            }
        else:
            products = _generic_smart_products(query_raw, context, margin)
            analysis_mode = "generic_market_fallback"
            evidence = {
                "summary": f"Sin coincidencia local; se genero una busqueda comercial para {query_raw}.",
                "detected_text": [query_raw],
                "visual_or_audio_clues": ["consulta textual amplia"],
                "uncertainties": ["Precios estimados: valida ofertas actuales, DOT/ficha tecnica y garantia."],
            }

    live_products = (
        _search_mercadolibre_products(query_raw, context, margin, limit=SMART_LIVE_SEARCH_LIMIT)
        if query_raw
        else []
    )
    products = _merge_product_lists(products, live_products)
    if query_raw:
        products = _ensure_minimum_options(products, query_raw, context, margin)
        products = _enrich_products_with_serpapi_images(products, query_raw)
        if live_products and analysis_mode == "smart_search_catalog":
            analysis_mode = "smart_search_marketplace"
            evidence["summary"] = f"Opciones de compra para: {query_raw}"
        evidence["uncertainties"] = list(
            dict.fromkeys(
                [
                    *evidence.get("uncertainties", []),
                    "Precios ordenados de menor a mayor; valida precio final, stock y garantia en el enlace.",
                ]
            )
        )

    return jsonify(
        {
            "ok": True,
            "mode": analysis_mode,
            "analysis_mode": analysis_mode,
            "query": query_raw,
            "country": context["country"],
            "currency": context["currency"],
            "marketplace_hint": context["marketplace"],
            "evidence": evidence,
            "margin": margin,
            "total_productos": len(products),
            "products": products,
        }
    )


@app.route("/api/smart-analyze-media", methods=["POST"])
def smart_analyze_media():
    file = (
        request.files.get("media")
        or request.files.get("image")
        or request.files.get("audio")
    )
    if not file:
        return jsonify({"error": "Sube una imagen o audio para analizar."}), 400

    mime_type = file.mimetype or ""
    if not (mime_type.startswith("image/") or mime_type.startswith("audio/")):
        return jsonify({"error": "Formato no soportado. Usa imagen o audio."}), 400

    media_bytes = file.read()
    if len(media_bytes) > 15 * 1024 * 1024:
        return jsonify({"error": "Archivo demasiado grande. Usa maximo 15 MB."}), 400

    country = request.form.get("country", "US")
    currency = request.form.get("currency", "")
    margin = float(request.form.get("margin") or 30)
    query = request.form.get("query", "")
    category = request.form.get("category", "")
    context = _market_context(country, currency)

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return jsonify(
            {
                "ok": False,
                "error": "Falta GEMINI_API_KEY en el backend.",
                "analysis_mode": "missing_gemini_key",
                "blocked": True,
                "block_reason": "No existe GEMINI_API_KEY o GOOGLE_API_KEY en el entorno.",
                "country": context["country"],
                "currency": context["currency"],
                "marketplace_hint": context["marketplace"],
            }
        ), 500

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        media_part = types.Part.from_bytes(data=media_bytes, mime_type=mime_type)
        instruction = (
            f"{SMART_SEARCH_PROMPT}\nPais: {context['country']}.\n"
            f"Moneda: {context['currency']}.\nMarketplace sugerido: {context['marketplace']}.\n"
            f"Cultura/tono: {context['tone']}.\nMargen de ganancia: {margin}%.\n"
            f"Consulta adicional del usuario: {query or 'sin texto'}.\n"
            f"Categoria elegida: {category or 'todas'}."
        )
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[media_part, instruction],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.25,
            ),
        )
        payload = _extract_json(response.text)
        payload["analysis_mode"] = (
            "gemini_audio_search" if mime_type.startswith("audio/") else "gemini_image_search"
        )
        payload["ai_provider"] = "gemini"
        payload["model"] = GEMINI_MODEL

    except Exception as exc:
        return jsonify(
            {
                "ok": False,
                "error": "Fallo el analisis multimedia con Gemini.",
                "analysis_mode": "gemini_error",
                "blocked": True,
                "block_reason": str(exc),
                "country": context["country"],
                "currency": context["currency"],
                "marketplace_hint": context["marketplace"],
                "margin": margin,
                "evidence": {
                    "summary": "Gemini fallo durante el analisis de imagen/audio.",
                    "detected_text": [query or file.filename],
                    "visual_or_audio_clues": [file.filename],
                    "uncertainties": [str(exc)],
                },
            }
        ), 500

    if payload.get("blocked"):
        return jsonify(payload), 200

    products = _extract_smart_products(payload)
    if products:
        products = _normalize_smart_products(products, context["currency"], margin)
    else:
        return jsonify(
            {
                "ok": False,
                "error": "Gemini respondio, pero no devolvio productos utilizables.",
                "analysis_mode": "gemini_empty_products",
                "blocked": True,
                "block_reason": "La respuesta de Gemini no trajo products/productos validos.",
                "raw_payload_preview": str(payload)[:800],
                "country": context["country"],
                "currency": context["currency"],
                "marketplace_hint": context["marketplace"],
            }
        ), 422

    provider_query = query or (products[0].get("search_query") if products else "") or file.filename
    products = _merge_product_lists(
        products,
        _search_mercadolibre_products(provider_query, context, margin, limit=SMART_LIVE_SEARCH_LIMIT),
    )
    products = _ensure_minimum_options(products, provider_query, context, margin)
    products = _enrich_products_with_serpapi_images(products, provider_query)
    evidence = payload.get("evidence") or {}
    evidence["uncertainties"] = list(
        dict.fromkeys(
            [
                *evidence.get("uncertainties", []),
                "Precios ordenados de menor a mayor; valida precio final, stock y garantia en el enlace.",
            ]
        )
    )
    payload["evidence"] = evidence

    payload.update(
        {
            "ok": True,
            "country": payload.get("country") or context["country"],
            "currency": payload.get("currency") or context["currency"],
            "marketplace_hint": payload.get("marketplace_hint") or context["marketplace"],
            "margin": margin,
            "total_productos": len(products),
            "products": products,
        }
    )
    return jsonify(payload)


@app.route("/api/diagnostico", methods=["POST", "GET"])
def diagnostico():
    if request.method == "GET":
        return (
            jsonify(
                {
                    "error": (
                        "Este endpoint acepta POST con multipart/form-data y "
                        "una imagen en el campo foto, imagen o image."
                    )
                }
            ),
            405,
        )

    file = (
        request.files.get("foto")
        or request.files.get("imagen")
        or request.files.get("image")
    )
    if not file:
        return jsonify({"error": "No llego ninguna imagen."}), 400

    image_bytes = file.read()
    mime_type = file.mimetype or "image/jpeg"
    try:
        img = Image.open(BytesIO(image_bytes))
        img.verify()
        img = Image.open(BytesIO(image_bytes))
    except Exception as exc:
        return jsonify({"error": f"No se pudo abrir la imagen: {exc}"}), 400

    pais = request.form.get("pais", "PE").upper()
    simbolo, _factor = MONEDAS.get(pais, MONEDAS["OTRO"])
    gemini_error = ""
    diagnostico_ai = None
    try:
        diagnostico_ai = _analizar_imagen_con_gemini(image_bytes, mime_type, pais)
    except Exception as exc:
        gemini_error = str(exc)

    rostro_detectado = (
        bool(diagnostico_ai.get("rostro_detectado"))
        if diagnostico_ai
        else _detectar_rostro(img)
    )

    if diagnostico_ai:
        tipo_piel = diagnostico_ai.get("tipo_piel", "No determinado")
        subtono = diagnostico_ai.get("subtono", "No determinado")
        recomendacion = diagnostico_ai.get("recomendacion", "")
        analisis_modo = "gemini_vision"
    elif rostro_detectado:
        tipo_piel = "Mixta"
        subtono = "Neutro"
        recomendacion = (
            "Rutina equilibrada: limpieza suave, hidratacion ligera, "
            "proteccion solar y acabado mate en zona T. Activa GEMINI_API_KEY "
            "para obtener analisis visual real por foto."
        )
        analisis_modo = "local_fallback"
    else:
        tipo_piel = "No determinado"
        subtono = "No determinado"
        recomendacion = (
            "No se detecto un rostro claro. Puedes probar con una foto frontal "
            "y buena luz; activa GEMINI_API_KEY para analisis visual avanzado."
        )
        analisis_modo = "local_fallback"

    try:
        productos = _productos_belleza(simbolo)
    except Exception as exc:
        return jsonify({"error": f"No se pudieron cargar productos: {exc}"}), 500
    productos = _productos_personalizados(productos, diagnostico_ai)

    total_productos = len(productos)
    inventario_total = sum(int(prod.get("stock") or 0) for prod in productos)
    if diagnostico_ai:
        analisis_productos = diagnostico_ai.get("resumen_venta") or (
            f"Se encontraron {total_productos} productos disponibles y se ordenaron "
            "segun el analisis visual de la foto."
        )
    else:
        analisis_productos = (
            f"Se encontraron {total_productos} productos disponibles en tu lista "
            f"con {inventario_total} unidades en inventario."
        )

    respuesta = {
        "analisis": "facial_producto",
        "analysis_mode": analisis_modo,
        "modelo": GEMINI_MODEL if diagnostico_ai else "local",
        "rostro_detectado": rostro_detectado,
        "tipo_piel": tipo_piel,
        "subtono": subtono,
        "recomendacion": recomendacion,
        "analisis_productos": analisis_productos,
        "total_productos": total_productos,
        "inventario_total": inventario_total,
        "productos": productos,
        "textos": CULTURA.get(pais, CULTURA["OTRO"]),
    }
    if diagnostico_ai:
        respuesta.update(
            {
                "confianza": diagnostico_ai.get("confianza"),
                "calidad_foto": diagnostico_ai.get("calidad_foto"),
                "nivel_grasa": diagnostico_ai.get("nivel_grasa"),
                "nivel_hidratacion": diagnostico_ai.get("nivel_hidratacion"),
                "textura": diagnostico_ai.get("textura"),
                "ojeras": diagnostico_ai.get("ojeras"),
                "sensibilidad": diagnostico_ai.get("sensibilidad"),
                "manchas_o_tono": diagnostico_ai.get("manchas_o_tono"),
                "labios": diagnostico_ai.get("labios"),
                "rutina_manana": diagnostico_ai.get("rutina_manana") or [],
                "rutina_noche": diagnostico_ai.get("rutina_noche") or [],
                "ingredientes_recomendados": diagnostico_ai.get("ingredientes_recomendados") or [],
                "evitar": diagnostico_ai.get("evitar") or [],
                "maquillaje_sugerido": diagnostico_ai.get("maquillaje_sugerido") or {},
            }
        )
    elif gemini_error:
        respuesta["gemini_error"] = gemini_error

    return jsonify(respuesta)


@app.route("/api/pedido", methods=["POST"])
def pedido():
    data = request.get_json(silent=True) or {}
    nombre = data.get("nombre", "")
    email = data.get("email", "")
    direccion = data.get("direccion", "")
    whatsapp = str(data.get("whatsapp", ""))
    carrito = data.get("carrito") or []

    total = sum(_leer_precio(item.get("precio")) * int(item.get("cantidad", 1)) for item in carrito)
    wa_msg = f"Hola! Soy {nombre}.\nQuiero pedir:\n"
    for item in carrito:
        wa_msg += (
            f"- {item.get('nombre', 'Producto')} x{item.get('cantidad', 1)} "
            f"({item.get('precio', '')})\n"
        )
    wa_msg += f"Total: {total:.2f}\nDireccion: {direccion}\nEmail: {email}"

    wa_number = whatsapp.lstrip("+").replace(" ", "")
    wa_url = f"https://wa.me/{wa_number}?text={urllib.parse.quote(wa_msg)}" if wa_number else ""
    return jsonify({"ok": True, "wa_url": wa_url})


@app.route("/api/validar-imagen-producto", methods=["POST"])
def validar_imagen_producto():
    data = request.get_json(silent=True) or {}
    publicacion = data.get("publicacion") or {}
    score = float(data.get("image_match_score") or publicacion.get("image_match_score") or 0)
    verified = bool(data.get("image_verified") or publicacion.get("image_verified"))
    image_url = str(data.get("image") or publicacion.get("image") or "")
    blocked_sources = ["source.unsplash.com", "picsum.photos", "placeholder"]
    blocked = any(source in image_url for source in blocked_sources)
    publish = verified and score >= IMAGE_MIN_SCORE and not blocked
    return jsonify(
        {
            "publish": publish,
            "reason": (
                "Imagen aprobada para publicar."
                if publish
                else "Imagen bloqueada: falta verificacion IA o la fuente es generica."
            ),
            "required_score": IMAGE_MIN_SCORE,
            "validation_prompt": IMAGE_VALIDATION_PROMPT,
        }
    )


@app.route("/<path:filename>")
def site_file(filename):
    normalized = filename.strip("/")
    if normalized.startswith("docs/"):
        normalized = normalized[5:]
    if normalized.startswith("api/"):
        return jsonify({"error": "Ruta API no encontrada o metodo no permitido."}), 404
    return _send_site_file(normalized)


# ── Orders ────────────────────────────────────────────────────────────────────

def _order_db():
    from product_platform import get_db
    return get_db()


def _make_order_id():
    import uuid
    return "ORD-" + uuid.uuid4().hex[:12].upper()


def _make_item_id():
    import uuid
    return "OIT-" + uuid.uuid4().hex[:10].upper()


def _now_str():
    from datetime import datetime
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


@app.route("/api/orders", methods=["POST"])
def create_order():
    """
    Create an order from the cart and initiate SafePay checkout.
    Body JSON:
    {
      "cart": [{"product_id": "...", "name": "...", "unit_price": 9.90,
                "quantity": 2, "currency": "USD", "sku": ""}],
      "customer": {"name":"","email":"","phone":"","address":"",
                   "city":"","state":"","zip":"","country":""},
      "shipping": 0,
      "tax": 0,
      "currency": "USD",
      "organization_id": ""   // optional
    }
    """
    data = request.get_json(silent=True) or {}
    cart = data.get("cart") or []
    if not cart:
        return jsonify({"ok": False, "error": "Cart is empty"}), 400

    customer = data.get("customer") or {}
    if not customer.get("email"):
        return jsonify({"ok": False, "error": "customer.email is required"}), 400

    currency = str(data.get("currency") or "USD").upper()
    shipping = float(data.get("shipping") or 0)
    tax = float(data.get("tax") or 0)
    org_id = data.get("organization_id") or ""

    # Calculate totals
    subtotal = sum(
        float(item.get("unit_price") or 0) * int(item.get("quantity") or 1)
        for item in cart
    )
    total = round(subtotal + shipping + tax, 2)
    subtotal = round(subtotal, 2)

    order_id = _make_order_id()
    now = _now_str()

    try:
        conn = _order_db()
        conn.execute(
            """
            INSERT INTO platform_orders
            (id, organization_id, customer_name, customer_email, customer_phone,
             customer_address, customer_city, customer_state, customer_zip,
             customer_country, subtotal, shipping, tax, total, currency,
             status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'pending_payment',?,?)
            """,
            (
                order_id, org_id,
                customer.get("name", ""), customer.get("email", ""),
                customer.get("phone", ""), customer.get("address", ""),
                customer.get("city", ""), customer.get("state", ""),
                customer.get("zip", ""), customer.get("country", ""),
                subtotal, shipping, tax, total, currency, now, now,
            ),
        )
        for item in cart:
            qty = int(item.get("quantity") or 1)
            unit = float(item.get("unit_price") or 0)
            conn.execute(
                """
                INSERT INTO platform_order_items
                (id, order_id, product_id, product_name, sku,
                 unit_price, quantity, subtotal, currency, snapshot_json)
                VALUES (?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    _make_item_id(), order_id,
                    item.get("product_id") or "",
                    item.get("name") or "Product",
                    item.get("sku") or "",
                    unit, qty, round(unit * qty, 2), currency,
                    json.dumps(item),
                ),
            )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[orders] DB error: {exc}", flush=True)
        return jsonify({"ok": False, "error": f"DB error: {exc}"}), 500

    # Call SafePay
    safepay_url = f"{SAFEPAY_API_URL}/api/payments/create"
    sp_body = {
        "amount": total,
        "currency": currency,
        "method": "Online",
        "description": f"Order {order_id} — {len(cart)} item(s)",
        "customer": customer.get("name", ""),
        "customer_email": customer.get("email", ""),
        "metadata": {"order_id": order_id},
    }
    print(f"[orders] Calling SafePay: {safepay_url} body={sp_body}", flush=True)

    try:
        import requests as _req
        resp = _req.post(safepay_url, json=sp_body, timeout=60)
        print(f"[orders] SafePay response {resp.status_code}: {resp.text[:400]}", flush=True)
        resp.raise_for_status()
        sp_result = resp.json()
    except ImportError:
        payload_bytes = json.dumps(sp_body).encode()
        import urllib.request as _ur
        req = _ur.Request(safepay_url, data=payload_bytes,
                          headers={"Content-Type": "application/json"}, method="POST")
        with _ur.urlopen(req, timeout=60) as r:
            sp_result = json.loads(r.read().decode())
    except Exception as exc:
        print(f"[orders] SafePay error: {exc}", flush=True)
        return jsonify({
            "ok": False,
            "error": f"Order created (id={order_id}) but SafePay failed: {exc}",
            "order_id": order_id,
            "total": total,
        }), 502

    sp_id = sp_result.get("id", "")
    checkout_url = sp_result.get("checkout_url") or f"{SAFEPAY_API_URL}/payment/{sp_id}"

    # Save SafePay reference
    try:
        conn = _order_db()
        conn.execute(
            "UPDATE platform_orders SET safepay_id=?, checkout_url=?, updated_at=? WHERE id=?",
            (sp_id, checkout_url, _now_str(), order_id),
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        print(f"[orders] Could not save safepay_id: {exc}", flush=True)

    return jsonify({
        "ok": True,
        "order_id": order_id,
        "safepay_id": sp_id,
        "total": total,
        "currency": currency,
        "checkout_url": checkout_url,
        "pay_url": checkout_url,
        "status": "pending_payment",
    }), 201


@app.route("/api/orders/<order_id>", methods=["GET"])
def get_order(order_id):
    """Return order status and items."""
    try:
        conn = _order_db()
        row = conn.execute(
            "SELECT * FROM platform_orders WHERE id=?", (order_id,)
        ).fetchone()
        if not row:
            conn.close()
            return jsonify({"ok": False, "error": "Order not found"}), 404
        items = conn.execute(
            "SELECT * FROM platform_order_items WHERE order_id=?", (order_id,)
        ).fetchall()
        conn.close()
        order = dict(row)
        order["items"] = [dict(i) for i in items]
        return jsonify({"ok": True, "order": order})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


@app.route("/api/orders/<order_id>/confirm", methods=["POST"])
def confirm_order(order_id):
    """
    Called by SafePay webhook or manually to mark an order as paid.
    Body: { "safepay_status": "pagado", "transaction_id": "..." }
    """
    data = request.get_json(silent=True) or {}
    sp_status = data.get("safepay_status") or data.get("status") or "pagado"
    tx_id = data.get("transaction_id") or ""
    now = _now_str()
    try:
        conn = _order_db()
        row = conn.execute(
            "SELECT * FROM platform_orders WHERE id=?", (order_id,)
        ).fetchone()
        if not row:
            conn.close()
            return jsonify({"ok": False, "error": "Order not found"}), 404
        conn.execute(
            """UPDATE platform_orders
               SET status='paid', safepay_status=?, updated_at=?
               WHERE id=?""",
            (sp_status, now, order_id),
        )
        conn.commit()
        conn.close()
        print(f"[orders] Order {order_id} marked PAID (tx={tx_id})", flush=True)
        return jsonify({"ok": True, "order_id": order_id, "status": "paid"})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500


# ── SafePay webhook (confirmacion automatica de pago) ─────────────────────────

@app.route("/api/safepay/webhook", methods=["GET", "POST"])
def safepay_webhook():
    """
    SafePay calls this URL after a successful payment.
    It sends the payment id and order metadata, we mark the order as paid.
    GET: health-check so you can verify the endpoint is reachable.
    """
    if request.method == "GET":
        return jsonify({"ok": True, "status": "webhook endpoint active", "hint": "POST to confirm a payment"}), 200
    data = request.get_json(silent=True) or {}
    print(f"[safepay-webhook] received: {data}", flush=True)
    sp_id = data.get("id") or data.get("payment_id") or ""
    sp_status = data.get("status") or ""
    metadata = data.get("metadata") or {}
    order_id = metadata.get("order_id") or data.get("order_id") or ""

    if not order_id:
        # Try to find order by safepay_id
        try:
            conn = _order_db()
            row = conn.execute(
                "SELECT id FROM platform_orders WHERE safepay_id=?", (sp_id,)
            ).fetchone()
            conn.close()
            if row:
                order_id = dict(row)["id"]
        except Exception:
            pass

    if order_id and sp_status in ("pagado", "paid", "completado", "completed"):
        try:
            conn = _order_db()
            conn.execute(
                "UPDATE platform_orders SET status='paid', safepay_status=?, updated_at=? WHERE id=?",
                (sp_status, _now_str(), order_id),
            )
            conn.commit()
            conn.close()
            print(f"[safepay-webhook] Order {order_id} → PAID", flush=True)
        except Exception as exc:
            print(f"[safepay-webhook] DB update failed: {exc}", flush=True)

    return jsonify({"ok": True}), 200

@app.route("/api/safepay/checkout", methods=["POST"])
def safepay_checkout():
    """
    Crea un pago en SafePay y devuelve la URL de pago.
    Body JSON esperado:
      { "product_name": "...", "amount": 99.90, "currency": "PEN",
        "customer": "...", "customer_email": "..." }
    Respuesta:
      { "ok": true, "pay_url": "https://...", "payment_id": "SP-..." }
    """
    data = request.get_json(silent=True) or {}
    print(f"[safepay] request body: {data}", flush=True)
    print(f"[safepay] SAFEPAY_API_URL = {SAFEPAY_API_URL!r}", flush=True)

    amount = float(data.get("amount") or data.get("importe") or data.get("monto") or 0)
    if amount <= 0:
        return jsonify({"ok": False, "error": "El monto debe ser mayor a 0"}), 400

    safepay_url = f"{SAFEPAY_API_URL}/api/payments/create"
    body = {
        "amount":         amount,   # siempre en inglés
        "currency":       data.get("currency") or data.get("moneda", "PEN"),
        "method":         "Online",
        "description":    data.get("product_name") or data.get("description") or data.get("producto") or "Compra",
        "customer":       data.get("customer") or data.get("cliente", ""),
        "customer_email": data.get("customer_email") or data.get("email", ""),
    }
    print(f"[safepay] POST {safepay_url} body={body}", flush=True)

    try:
        try:
            import requests as _requests
            resp = _requests.post(safepay_url, json=body, timeout=60)
            print(f"[safepay] HTTP {resp.status_code} response: {resp.text[:500]}", flush=True)
            resp.raise_for_status()
            result = resp.json()
        except ImportError:
            # Fallback a urllib si requests no está instalado
            payload_bytes = json.dumps(body).encode()
            req = urllib.request.Request(
                safepay_url,
                data=payload_bytes,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read().decode()
            print(f"[safepay] urllib response: {raw[:500]}", flush=True)
            result = json.loads(raw)
    except Exception as exc:
        tb = traceback.format_exc()
        print(f"[safepay] ERROR: {exc}\n{tb}", flush=True)
        return jsonify({
            "ok":          False,
            "error":       f"SafePay no disponible: {exc}",
            "safepay_url": safepay_url,
            "detail":      tb.splitlines()[-1] if tb else "",
        }), 503

    pay_id = result.get("id", "")
    checkout_url = result.get("checkout_url") or f"{SAFEPAY_API_URL}/payment/{pay_id}"
    print(f"[safepay] pay_id={pay_id!r} checkout_url={checkout_url!r}", flush=True)

    return jsonify({
        "ok":           True,
        "payment_id":   pay_id,
        "status":       result.get("status", "pendiente"),
        "pay_url":      checkout_url,
        "checkout_url": checkout_url,
    })


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
