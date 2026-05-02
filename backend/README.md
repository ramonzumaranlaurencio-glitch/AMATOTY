# Backend AMATOTY

## Que hace

- Expone una API Flask para validar que el backend esta activo.
- Recibe imagenes por POST en `/analisis`.
- Recibe diagnostico facial/producto por POST en `/api/diagnostico`.
- Si configuras `GEMINI_API_KEY`, el diagnostico usa Gemini 2.5 Flash con vision
  y respuesta JSON estructurada para que cada foto tenga un analisis real.
- `/api/smart-analyze-media` analiza imagen/audio de producto con Gemini. Para
  una foto como una lavadora, debe devolver minimo 10 opciones comprables,
  ordenadas por precio, y completa con miniaturas reales de marketplace cuando
  Mercado Libre responde.
- Si no hay `GEMINI_API_KEY`, la busqueda usa texto o nombre de archivo como
  pista; no puede reconocer pixeles reales sin esa clave.
- Recibe pedidos por POST en `/api/pedido`.
- El archivo que Render debe arrancar es `main.py`.

## Uso rapido

1. Instala dependencias:

```bash
pip install -r requirements.txt
```

Configura la clave de Gemini antes de ejecutar si quieres analisis real:

```bash
set GEMINI_API_KEY=tu_clave
```

En PowerShell:

```powershell
$env:GEMINI_API_KEY="tu_clave"
```

2. Ejecuta el backend local:

```bash
python main.py
```

3. En Render usa este Start Command si el Root Directory es `backend`:

```bash
gunicorn main:app
```

Si Render usa la raiz del repositorio como Root Directory, el Start Command debe ser:

```bash
gunicorn backend.main:app
```

Despues de publicar, prueba que Render tenga la ruta activa:

```bash
curl https://amatoty.onrender.com/api/diagnostico
```

Debe responder JSON con estado 405. Si responde una pagina HTML 404, Render todavia
esta usando un deploy viejo o un Start Command distinto.

## Render y Gemini

En Render agrega esta variable en `Environment`:

```text
GEMINI_API_KEY=tu_clave_de_google_ai_studio
```

Opcionalmente puedes cambiar el modelo:

```text
GEMINI_MODEL=gemini-2.5-flash
```

Si `analysis_mode` responde `gemini_vision`, ya esta usando analisis real. Si
responde `local_fallback`, falta la clave o la dependencia `google-genai`.
