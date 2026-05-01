import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
import urllib.parse

app = Flask(__name__)

# Configuración de email (ajusta estos valores)
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'TU_EMAIL@gmail.com'
SMTP_PASS = 'TU_APP_PASSWORD'
EMAIL_DESTINO = 'DESTINO@tucorreo.com'

@app.route('/api/pedido', methods=['POST'])
def recibir_pedido():
    data = request.json
    nombre = data.get('nombre')
    email = data.get('email')
    direccion = data.get('direccion')
    whatsapp = data.get('whatsapp')
    carrito = data.get('carrito', [])
    resumen = f"Pedido de: {nombre}\nEmail: {email}\nDirección: {direccion}\nWhatsApp: {whatsapp}\n\nProductos:\n"
    for item in carrito:
        resumen += f"- {item.get('nombre')} x{item.get('cantidad',1)} ({item.get('precio')})\n"
    total = sum(float((item.get('precio') or '').replace('S/','').replace(',','.').strip() or 0)*item.get('cantidad',1) for item in carrito)
    resumen += f"\nTotal: S/ {total:.2f}\n"
    # Enviar email
    try:
        msg = MIMEText(resumen)
        msg['Subject'] = 'Nuevo pedido Oye Bonita'
        msg['From'] = SMTP_USER
        msg['To'] = EMAIL_DESTINO
        s = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        s.starttls()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, [EMAIL_DESTINO], msg.as_string())
        s.quit()
    except Exception as ex:
        print('Error enviando email:', ex)
    # Generar enlace WhatsApp
    wa_msg = f"Hola! Soy {nombre}.\nQuiero pedir:\n"
    for item in carrito:
        wa_msg += f"- {item.get('nombre')} x{item.get('cantidad',1)} ({item.get('precio')})\n"
    wa_msg += f"Total: S/ {total:.2f}\nDirección: {direccion}\nEmail: {email}"
    wa_url = f"https://wa.me/{whatsapp.lstrip('+').replace(' ','')}?text={urllib.parse.quote(wa_msg)}"
    return jsonify({'ok':True, 'wa_url': wa_url})

if __name__ == '__main__':
    app.run(port=5050, debug=True)
