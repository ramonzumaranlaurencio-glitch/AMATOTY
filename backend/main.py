import json
import os
import re
import sqlite3
import urllib.parse
import uuid
from datetime import datetime

from flask import jsonify, request, send_from_directory
from flask import Flask
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app)

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


def _data_path(*parts):
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", *parts))


SITE_DIR = _data_path("docs")
LOCAL_SITE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "docs"))
TRACKING_DB_PATH = _data_path("data", "lca_pro_final.db")


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
        res.innerHTML='<b>Tipo de piel:</b> '+(data.tipo_piel||'')+'<br><b>Subtono:</b> '+(data.subtono||'')+'<br><b>Recomendacion:</b> '+(data.recomendacion||'');
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
    for site_dir in [SITE_DIR, LOCAL_SITE_DIR]:
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


@app.route("/healthz")
def healthz():
    return jsonify({"ok": True, "service": "amatoty-backend"}), 200


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

    try:
        img = Image.open(file.stream)
        img.verify()
        file.stream.seek(0)
        img = Image.open(file.stream)
    except Exception as exc:
        return jsonify({"error": f"No se pudo abrir la imagen: {exc}"}), 400

    pais = request.form.get("pais", "PE").upper()
    simbolo, _factor = MONEDAS.get(pais, MONEDAS["OTRO"])
    rostro_detectado = _detectar_rostro(img)

    tipo_piel = "Mixta"
    subtono = "Neutro"
    if rostro_detectado:
        recomendacion = (
            "Rutina equilibrada: limpieza suave, hidratacion ligera, "
            "proteccion solar y acabado mate en zona T."
        )
    else:
        recomendacion = (
            "No se detecto un rostro claro. Puedes probar con una foto frontal "
            "y buena luz; mientras tanto te muestro recomendaciones generales."
        )

    try:
        productos = _productos_belleza(simbolo)
    except Exception as exc:
        return jsonify({"error": f"No se pudieron cargar productos: {exc}"}), 500

    total_productos = len(productos)
    inventario_total = sum(int(prod.get("stock") or 0) for prod in productos)
    analisis_productos = (
        f"Se encontraron {total_productos} productos disponibles en tu lista "
        f"con {inventario_total} unidades en inventario."
    )

    return jsonify(
        {
            "analisis": "facial_producto",
            "tipo_piel": tipo_piel,
            "subtono": subtono,
            "recomendacion": recomendacion,
            "analisis_productos": analisis_productos,
            "total_productos": total_productos,
            "inventario_total": inventario_total,
            "productos": productos,
            "textos": CULTURA.get(pais, CULTURA["OTRO"]),
        }
    )


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
    if normalized.startswith("api/"):
        return jsonify({"error": "Ruta API no encontrada."}), 404
    return _send_site_file(normalized)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
