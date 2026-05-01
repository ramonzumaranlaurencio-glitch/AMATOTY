from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/")
def home():
    return "AMATOTY backend activo", 200


@app.route("/analisis", methods=["POST"])
def analisis():
    if "imagen" not in request.files:
        return jsonify({"error": "No hay imagen"}), 400
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5050)
