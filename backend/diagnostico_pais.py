
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image
import io
import json
import os
from product_image_ai import describe_image_from_url

CORS_ORIGINS = ["*"]  # Puedes restringir a tu dominio real en producción
app = Flask(__name__)
CORS(app, origins=CORS_ORIGINS)

@app.route('/api/explicar-imagen', methods=['POST'])
def explicar_imagen():
    data = request.get_json()
    image_url = data.get('image_url')
    descripcion = ''
    if image_url:
        try:
            descripcion = describe_image_from_url(image_url)
        except Exception as e:
            descripcion = f"Error IA: {str(e)}"
    return jsonify({'descripcion': descripcion})

MONEDAS = {
    'PE': ('S/', 1.40, 'Perú'),
    'MX': ('MXN', 1.40, 'México'),
    'CL': ('CLP', 1.40, 'Chile'),
    'CO': ('COP', 1.25, 'Colombia'),
    'AR': ('ARS', 1.40, 'Argentina'),
    'US': ('USD', 1.40, 'Estados Unidos'),
    'EC': ('USD', 1.40, 'Ecuador'),
    'BO': ('BOB', 1.40, 'Bolivia'),
    'PY': ('PYG', 1.40, 'Paraguay'),
    'UY': ('UYU', 1.40, 'Uruguay'),
    'BR': ('BRL', 1.40, 'Brasil'),
    'VE': ('VES', 1.40, 'Venezuela'),
    'OTRO': ('USD', 1.40, 'Otro')
}

CULTURA = {
    'PE': {'carrito': 'carrito', 'btn_agregar': 'Agregar al carrito'},
    'MX': {'carrito': 'carrito', 'btn_agregar': 'Añadir al carrito'},
    'CL': {'carrito': 'carrito', 'btn_agregar': 'Agregar al carrito'},
    'CO': {'carrito': 'canasta', 'btn_agregar': 'Agregar a la canasta'},
    'AR': {'carrito': 'canasta', 'btn_agregar': 'Sumar a la canasta'},
    'US': {'carrito': 'cart', 'btn_agregar': 'Add to cart'},
    'EC': {'carrito': 'carrito', 'btn_agregar': 'Agregar al carrito'},
    'BO': {'carrito': 'carrito', 'btn_agregar': 'Agregar al carrito'},
    'PY': {'carrito': 'carrito', 'btn_agregar': 'Agregar al carrito'},
    'UY': {'carrito': 'carrito', 'btn_agregar': 'Agregar al carrito'},
    'BR': {'carrito': 'carrinho', 'btn_agregar': 'Adicionar ao carrinho'},
    'VE': {'carrito': 'carrito', 'btn_agregar': 'Agregar al carrito'},
    'OTRO': {'carrito': 'carrito', 'btn_agregar': 'Agregar al carrito'}
}

@app.route('/api/diagnostico', methods=['POST'])
def diagnostico():
    try:
        pais = request.form.get('pais', 'PE')
        file = request.files['foto']
        try:
            img = Image.open(file.stream)
        except Exception as e_img:
            return jsonify({
                'error': True,
                'productos': [{
                    'nombre': 'Error de imagen',
                    'marca': '',
                    'imagen': '',
                    'desc': f'No se pudo abrir la imagen: {str(e_img)}',
                    'precio': ''
                }]
            })
        # Aquí iría tu análisis real, simulado para ejemplo:
        tipo_piel = 'Mixta'
        subtono = 'Neutro'
        recomendacion = 'Rutina equilibrada con hidratación ligera y protección solar.'
        moneda, margen, pais_nombre = MONEDAS.get(pais, ('USD', 1.40, 'Otro'))
        cultura = CULTURA.get(pais, CULTURA['OTRO'])
        productos = []
        trending_path = os.path.join(os.path.dirname(__file__), '..', 'docs', 'assets', 'trending_products.json')
        try:
            with open(trending_path, encoding='utf-8') as f:
                trending = json.load(f)
            for prod in trending.get('products', []):
                cat = (prod.get('category') or '').lower()
                name = (prod.get('name') or '').lower()
                brand = (prod.get('brand') or '').lower()
                if any(x in cat for x in ['belleza', 'skin', 'facial', 'cosmético', 'dermo']) or any(x in name for x in ['skin', 'facial', 'serum', 'hidratante', 'protector', 'limpiador']) or any(x in brand for x in ['oye bonita', 'loreal', 'neutrogena', 'nivea', 'eucerin', 'cerave']):
                    precio_base = 50
                    if 'price' in prod:
                        try:
                            precio_base = float(prod['price'])
                        except:
                            pass
                    precio = precio_base * margen
                    productos.append({
                        'nombre': prod.get('name', 'Producto tendencia'),
                        'marca': prod.get('brand', ''),
                        'imagen': prod.get('image', ''),
                        'desc': prod.get('short_desc', prod.get('seo_title', 'Producto en tendencia')),
                        'precio': f"{moneda} {precio:.2f}"
                    })
            if not productos:
                for prod in trending.get('products', []):
                    precio_base = 50
                    if 'price' in prod:
                        try:
                            precio_base = float(prod['price'])
                        except:
                            pass
                    precio = precio_base * margen
                    productos.append({
                        'nombre': prod.get('name', 'Producto tendencia'),
                        'marca': prod.get('brand', ''),
                        'imagen': prod.get('image', ''),
                        'desc': prod.get('short_desc', prod.get('seo_title', 'Producto en tendencia')),
                        'precio': f"{moneda} {precio:.2f}"
                    })
        except Exception as e_prod:
            return jsonify({
                'error': True,
                'productos': [{
                    'nombre': 'Error de productos',
                    'marca': '',
                    'imagen': '',
                    'desc': f'No se pudo cargar productos: {str(e_prod)}',
                    'precio': ''
                }]
            })
        return jsonify({
            'tipo_piel': tipo_piel,
            'subtono': subtono,
            'recomendacion': recomendacion,
            'productos': productos,
            'textos': cultura
        })
    except Exception as e:
        return jsonify({
            'error': True,
            'productos': [{
                'nombre': 'Error inesperado',
                'marca': '',
                'imagen': '',
                'desc': f'Error inesperado: {str(e)}',
                'precio': ''
            }]
        })

if __name__ == '__main__':
    app.run(port=5050, debug=True)
