from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

IMAGE_MIN_SCORE = 0.82
IMAGE_VALIDATION_PROMPT = (
    "Analiza la imagen y el producto esperado. Responde SOLO JSON con match, "
    "score, caption, detected_objects y reason. Marca match=false si la imagen "
    "parece decorativa, paisaje, placeholder, producto distinto, empaque "
    "ilegible o foto generica."
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


@app.route("/api/validar-imagen-producto", methods=["POST"])
def validar_imagen_producto():
    data = request.get_json(silent=True) or {}
    score = float(data.get("image_match_score") or 0)
    verified = bool(data.get("image_verified"))
    image_url = str(data.get("image") or "")
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
