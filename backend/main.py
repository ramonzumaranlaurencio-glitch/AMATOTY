from flask import Flask, jsonify, request
from flask_cors import CORS

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
