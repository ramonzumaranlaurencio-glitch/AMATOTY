# Backend AMATOTY

## Que hace

- Expone una API Flask para validar que el backend esta activo.
- Recibe imagenes por POST en `/analisis`.
- El archivo que Render debe arrancar es `main.py`.

## Uso rapido

1. Instala dependencias:

```bash
pip install -r requirements.txt
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
