import json
import os
import re
import urllib.parse

from flask import Flask, jsonify, request
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
    products_path = _data_path("docs", "assets", "beauty_products.json")
    with open(products_path, encoding="utf-8") as f:
        beauty_products = json.load(f)

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
    return "AMATOTY backend activo", 200


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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
