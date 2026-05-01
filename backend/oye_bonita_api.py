import json
import os
import sys

from flask import Flask, jsonify, request
from flask_cors import CORS
from PIL import Image

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
CORS(app, origins=["https://systamato.github.io"])


@app.route("/")
def home():
    return "Backend AMATOTY activo. Usa /analisis con POST e imagen.", 200


@app.route("/analisis", methods=["POST"])
def analisis():
    return jsonify({"ok": True})


def diagnostico_real(img):
    import mediapipe as mp
    import numpy as np

    mp_face = mp.solutions.face_detection
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        img_rgb = img.convert("RGB")
        results = face_detection.process(np.array(img_rgb))
        if not results.detections:
            tipo_piel = "Desconocido"
            subtono = "Desconocido"
            color_labios = "Natural"
            tono_polvo = "Universal"
            recomendacion = "No se detecto rostro. Sube una foto clara y frontal."
        else:
            tipo_piel = "Mixta"
            subtono = "Neutro"
            color_labios = "Rosa"
            tono_polvo = "Medio"
            recomendacion = (
                f"Piel {tipo_piel}, subtono {subtono}. "
                f"Sugerimos labial {color_labios} y polvo {tono_polvo}."
            )

    products_path = os.path.join(
        os.path.dirname(__file__), "..", "docs", "assets", "beauty_products.json"
    )
    productos = []
    try:
        with open(products_path, encoding="utf-8") as f:
            beauty_products = json.load(f)
        for prod in beauty_products:
            categoria = prod.get("categoria", "").lower()
            if tipo_piel in prod.get("tipo_piel_recomendado", "") or categoria in [
                "base",
                "sellado",
                "labial",
                "rubor",
            ]:
                productos.append(
                    {
                        "nombre": prod.get("nombre"),
                        "marca": prod.get("marca"),
                        "categoria": prod.get("categoria"),
                        "desc": prod.get(
                            "resultados_esperados", prod.get("beneficios", [""])
                        )
                        or "",
                        "precio": f"{prod.get('currency', 'PEN')} {prod.get('precio', 0):.2f}",
                        "imagen": prod.get("imagen_ref", ""),
                    }
                )
    except Exception as e:
        productos = [
            {
                "nombre": "Error al cargar productos",
                "marca": "",
                "categoria": "",
                "desc": str(e),
                "precio": "",
                "imagen": "",
            }
        ]

    return {
        "tipo_piel": tipo_piel,
        "subtono": subtono,
        "color_labios": color_labios,
        "tono_polvo": tono_polvo,
        "recomendacion": recomendacion,
        "productos": productos,
    }


@app.route("/api/diagnostico", methods=["POST", "GET"])
def api_diagnostico():
    if request.method == "GET":
        return (
            jsonify(
                {
                    "error": (
                        "Este endpoint solo acepta POST con una imagen para "
                        "analisis facial."
                    )
                }
            ),
            405,
        )
    file = request.files.get("foto") or request.files.get("imagen")
    if not file:
        return (
            jsonify(
                {"error": "No llego ninguna imagen. El campo debe llamarse foto o imagen"}
            ),
            400,
        )
    img = Image.open(file.stream)
    pais = request.form.get("pais", "PE").upper()
    monedas = {
        "PE": ("S/", "PEN"),
        "MX": ("MXN", "MXN"),
        "CL": ("CLP", "CLP"),
        "CO": ("COP", "COP"),
        "AR": ("ARS", "ARS"),
        "US": ("USD", "USD"),
        "EC": ("USD", "USD"),
        "BO": ("BOB", "BOB"),
        "PY": ("PYG", "PYG"),
        "UY": ("UYU", "UYU"),
        "BR": ("BRL", "BRL"),
        "VE": ("VES", "VES"),
        "OTRO": ("USD", "USD"),
    }
    simbolo, _moneda = monedas.get(pais, ("USD", "USD"))
    resultado = diagnostico_real(img)
    for prod in resultado["productos"]:
        if "precio" in prod and prod["precio"]:
            try:
                monto = float(prod["precio"].split()[-1])
                prod["precio"] = f"{simbolo} {monto:.2f}"
            except ValueError:
                pass
    return jsonify(resultado)


if __name__ == "__main__":
    app.run(port=5050, debug=True)
