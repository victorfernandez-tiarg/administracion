# Deploy en Render (~$7/mes) o Railway (~$5/mes)

## Opción A — Render (recomendado)

1. Crear cuenta en https://render.com
2. New → Web Service → conectar repo de GitHub
3. Configurar:
   - **Runtime**: Docker
   - **Dockerfile Path**: `deploy/Dockerfile`
   - **Port**: 8501
4. Deploy ✓

### Actualizar datos en producción

Como el VPS no tiene acceso a tu red local, hay dos estrategias:

**Estrategia 1 (más simple): subir los .xlsx por el dashboard**
Agregar un `st.file_uploader` en el sidebar para subir los archivos directamente
desde el browser. El ETL los procesa en el momento.

**Estrategia 2 (más automatizada): sincronizar via Google Drive**
1. Subir los .xlsx exportados a una carpeta de Google Drive compartida
2. El script de ETL descarga automáticamente desde Drive usando `gdown`
3. Se puede programar para que corra cada X horas

Para activar la Estrategia 1, agregar en `dashboard/app.py` sidebar:
```python
st.markdown("---")
st.markdown("**Subir archivos**")
f1 = st.file_uploader("facturas.xlsx", type="xlsx")
f2 = st.file_uploader("cuentas_corrientes.xlsx", type="xlsx")
if f1:
    with open("data/raw/facturas.xlsx", "wb") as f:
        f.write(f1.read())
if f2:
    with open("data/raw/cuentas_corrientes.xlsx", "wb") as f:
        f.write(f2.read())
```

## Opción B — Railway

1. Crear cuenta en https://railway.app
2. New Project → Deploy from GitHub repo
3. Agregar variable de entorno: PORT=8501
4. Railway detecta el Dockerfile automáticamente

## Seguridad básica (opcional)

Para que el dashboard no sea público, agregar en `dashboard/app.py`:
```python
import streamlit_authenticator as stauth
# Ver documentación: https://github.com/mkhorasani/Streamlit-Authenticator
```

O usar la autenticación nativa de Render/Railway para proteger la URL.
