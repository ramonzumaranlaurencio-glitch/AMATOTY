from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import os
import sys
import json
import mediapipe as mp
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Importa tu clase o función real de Oye Bonita aquí
# from oyebonita import OyeBonitaPOS


app = Flask(__name__)
CORS(app, origins=["https://systamato.github.io"])

# Simulación: reemplaza esto por tu lógica real
# Instancia global (si tu clase lo permite)
# oye_bonita = OyeBonitaPOS(None)

def diagnostico_real(img):
    # --- Análisis facial con mediapipe (simulado si no hay rostro) ---
    mp_face = mp.solutions.face_detection
    with mp_face.FaceDetection(model_selection=1, min_detection_confidence=0.5) as face_detection:
        img_rgb = img.convert('RGB')
        results = face_detection.process(np.array(img_rgb))
        if not results.detections:
            tipo_piel = "Desconocido"
            subtono = "Desconocido"
            color_labios = "Natural"
            tono_polvo = "Universal"
            recomendacion = "No se detectó rostro. Sube una foto clara y frontal."
        else:
            # Simulación: asignar valores según detección (puedes mejorar con IA real)
            tipo_piel = "Mixta"
            subtono = "Neutro"
            color_labios = "Rosa"
            tono_polvo = "Medio"
            recomendacion = f"Piel {tipo_piel}, subtono {subtono}. Sugerimos labial {color_labios} y polvo {tono_polvo}."

    # --- Leer productos desde JSON ---
    products_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'assets', 'beauty_products.json')
    productos = []
    try:
        with open(products_path, encoding='utf-8') as f:
            beauty_products = json.load(f)
        for prod in beauty_products:
            # Filtrar productos según tipo de piel, categoría, etc. (puedes mejorar lógica)
            if tipo_piel in prod.get('tipo_piel_recomendado', '') or prod.get('categoria','').lower() in ['base','sellado','labial','rubor']:
                productos.append({
                    'nombre': prod.get('nombre'),
                    'marca': prod.get('marca'),
                    'categoria': prod.get('categoria'),
                    'desc': prod.get('resultados_esperados', prod.get('beneficios', [''])) or '',
                    'precio': f"{prod.get('currency','PEN')} {prod.get('precio',0):.2f}",
                    'imagen': prod.get('imagen_ref', ''),
                })
    except Exception as e:
        productos = [{
            'nombre': 'Error al cargar productos',
            'marca': '',
            'categoria': '',
            'desc': str(e),
            'precio': '',
            'imagen': ''
        }]

    return {
        "tipo_piel": tipo_piel,
        "subtono": subtono,
        "color_labios": color_labios,
        "tono_polvo": tono_polvo,
        "recomendacion": recomendacion,
        "productos": productos
    }


@app.route('/api/diagnostico', methods=['POST', 'GET'])
def api_diagnostico():
    if request.method == 'GET':
        return jsonify({"error": "Este endpoint solo acepta POST con una imagen para análisis facial."}), 405
    file = request.files['foto']
    img = Image.open(file.stream)
    # Obtener país del formulario
    pais = request.form.get('pais', 'PE').upper()
    # Monedas por país
    MONEDAS = {
        'PE': ('S/', 'PEN'),
        'MX': ('MXN', 'MXN'),
        'CL': ('CLP', 'CLP'),
        'CO': ('COP', 'COP'),
        'AR': ('ARS', 'ARS'),
        'US': ('USD', 'USD'),
        'EC': ('USD', 'USD'),
        'BO': ('BOB', 'BOB'),
        'PY': ('PYG', 'PYG'),
        'UY': ('UYU', 'UYU'),
        'BR': ('BRL', 'BRL'),
        'VE': ('VES', 'VES'),
        'OTRO': ('USD', 'USD')
    }
    simbolo, moneda = MONEDAS.get(pais, ('USD', 'USD'))
    resultado = diagnostico_real(img)
    # Ajustar moneda en productos
    for prod in resultado['productos']:
        if 'precio' in prod and prod['precio']:
            try:
                monto = float(prod['precio'].split()[-1])
                prod['precio'] = f"{simbolo} {monto:.2f}"
            except:
                pass
    return jsonify(resultado)

if __name__ == '__main__':
    app.run(port=5050, debug=True)
