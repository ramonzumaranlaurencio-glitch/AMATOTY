@app.get("/")
def home():
    return "AMATOTY backend activo", 200

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route("/")
def home():
    return "AMATOTY backend activo", 200

app = Flask(__name__)

@app.route("/")
def home():
    return "AMATOTY backend activo", 200

@app.route("/analisis", methods=["POST"])
def analisis():
    if "imagen" not in request.files:
        return jsonify({"error": "No hay imagen"}), 400
    imagen = request.files["imagen"]
    return jsonify({
        "ok": True,
        "mensaje": "Imagen recibida"
    })
def google_trends(keyword: str):
    # Placeholder: Integrar con pytrends o scraping real
    return {"keyword": keyword, "trend": "alta"}

@app.get("/health")
def health():
    return {"status": "ok", "date": str(datetime.date.today())}
