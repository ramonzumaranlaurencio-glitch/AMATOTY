# Backend automático de productos tendencia

## ¿Qué hace?
- Expone una API con FastAPI para consultar y actualizar productos tendencia.
- Permite integración futura con Google Trends, Amazon, TikTok, etc.
- Incluye script auto_update.py para automatización diaria (cron job).

## Uso rápido

1. Instala dependencias:
   ```
pip install -r requirements.txt
   ```
2. Ejecuta el backend:
   ```
uvicorn main:app --reload
   ```
3. Ejecuta actualización automática:
   ```
python auto_update.py
   ```

## Extensión
- Integra pytrends, scraping, o APIs reales en auto_update.py y main.py.
- Conecta con tu web: la home ya lee trending_products.json dinámicamente.

## Seguridad
- No expongas la API públicamente sin autenticación.
- El JSON se actualiza en docs/assets/trending_products.json.

## Siguiente salto
- Cuando tengas ventas, conecta IA real y APIs de tendencias para automatización total.
