# VARIABLES DE ENTORNO - Finnegans BI + Google Drive Sync

## Paso 5: Variables requeridas para Railway

Configura estas variables en el dashboard de Railway para el deployment:

### 1. **GOOGLE_SERVICE_ACCOUNT_JSON** (CRÍTICA)
- **Descripción**: JSON del Service Account de Google Cloud
- **Valor**: El contenido completo del archivo JSON descargado de Google Cloud, **en una sola línea**
- **Ejemplo formato** (simplificado):
  ```json
  {"type":"service_account","project_id":"finnegans-bi","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...","client_email":"railway-finnegans-sync@finnegans-bi.iam.gserviceaccount.com","client_id":"...","auth_uri":"...","token_uri":"..."}
  ```
- **⚠️ IMPORTANTE**: 
  - El JSON completo debe estar en UNA SOLA LÍNEA
  - Los saltos de línea dentro de `private_key` deben ser `\n` (backslash-n literal)
  - NO copiar tal cual; procesar el JSON primero

### 2. **GOOGLE_DRIVE_FACTURACION_FILE_ID**
- **Descripción**: ID del archivo "datos_facturacion.xlsx" en Google Drive
- **Valor**: `1299321983`
- **Cómo obtenerlo**: De la URL del archivo: `https://drive.google.com/file/d/{FILE_ID}/view`

### 3. **GOOGLE_DRIVE_CC_FILE_ID**
- **Descripción**: ID del archivo "cc_clientes.xlsx" en Google Drive
- **Valor**: `257513436`
- **Cómo obtenerlo**: De la URL del archivo: `https://drive.google.com/file/d/{FILE_ID}/view`

### 4. **GOOGLE_DRIVE_COMPOSICION_FILE_ID**
- **Descripción**: ID del archivo de composición de saldos en Google Drive
- **Valor**: ID real del archivo (no URL completa)
- **Archivo destino local**: `data/raw/composicion_saldos.xlsx`
- **Uso**: habilita aging por composición y deuda por centro de costo

### 5. **AUTO_SYNC_DRIVE** (RECOMENDADO)
- **Descripción**: Define si el ETL sincroniza Drive por defecto
- **Valor recomendado**: `true`

### 6. **DISABLE_AI** (RECOMENDADO)
- **Descripción**: Deshabilita Ollama en producción (no está disponible en Railway)
- **Valor**: `true`
- **Porqué**: Streamlit no puede iniciar IA local en Railway. Evita errores de conexión.

### 7. **PORT** (OPCIONAL - Railway lo configura automáticamente)
- **Descripción**: Puerto en el que corre Streamlit
- **Valor**: `8501`
- **Nota**: Railway asigna esto automáticamente; omitir si no es necesario

## Pasos para configurar en Railway

1. Ir a https://railway.app (loggearse con GitHub)
2. Abrir el deployment de finnegans_bi
3. Click en **Variables** (o Environment)
4. Agregar cada variable:
   - Nombre exacto (case-sensitive): `GOOGLE_SERVICE_ACCOUNT_JSON`
   - Valor: pegar el JSON en una línea
5. Repetir para `GOOGLE_DRIVE_FACTURACION_FILE_ID`, `GOOGLE_DRIVE_CC_FILE_ID` y `GOOGLE_DRIVE_COMPOSICION_FILE_ID`
6. Agregar `AUTO_SYNC_DRIVE=true`
6. Guardar y Railway redeplegará automáticamente

## Cómo preparar GOOGLE_SERVICE_ACCOUNT_JSON para Railway

El JSON del service account descargado de Google Cloud se ve así:
```json
{
  "type": "service_account",
  "project_id": "finnegans-bi",
  "private_key_id": "abc123...",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBA...\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "railway-finnegans-sync@finnegans-bi.iam.gserviceaccount.com",
  ...
}
```

**Convertir a una línea**:
1. Copiar el JSON completo
2. Usar herramienta online (ej: https://tools.knightrider.digital/json-minifier/) o Python:
   ```python
   import json
   with open("service-account.json") as f:
       data = json.load(f)
   minified = json.dumps(data)
   print(minified)
   ```
3. Copiar el resultado (sin saltos de línea)
4. Pegarlo en la variable de Railway

## Testing local antes de Railway

Para probar localmente con las variables:

```bash
# En terminal, en la raíz del proyecto
export GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
export GOOGLE_DRIVE_FACTURACION_FILE_ID='1299321983'
export GOOGLE_DRIVE_CC_FILE_ID='257513436'
export GOOGLE_DRIVE_COMPOSICION_FILE_ID='TU_ID_COMPOSICION'
export AUTO_SYNC_DRIVE='true'
export DISABLE_AI='true'

# Luego correr
python etl/sync_drive.py  # Probar descarga
streamlit run dashboard/app.py  # Probar app
```

En Windows (PowerShell):
```powershell
$env:GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
$env:GOOGLE_DRIVE_FACTURACION_FILE_ID='1299321983'
$env:GOOGLE_DRIVE_CC_FILE_ID='257513436'
$env:GOOGLE_DRIVE_COMPOSICION_FILE_ID='TU_ID_COMPOSICION'
$env:AUTO_SYNC_DRIVE='true'
$env:DISABLE_AI='true'

streamlit run dashboard/app.py
```

## Confirmación de setup

Luego de agregar variables a Railway:
1. ✅ Deployment se redeploiará automáticamente
2. ✅ Logs en Railway deberían mostrar: "Sincronizando archivos desde Google Drive..."
3. ✅ Botón "⬇️ Sincronizar Drive" en sidebar debería funcionar
4. ✅ Tab "Facturación" y "Ctas. Ctes." con datos actualizados
5. ✅ En "Cuentas Corrientes" aparece "Fuente de vencimiento activa: composicion" (si el archivo está disponible)

## Troubleshooting

| Problema | Solución |
|----------|----------|
| `GOOGLE_SERVICE_ACCOUNT_JSON no está definida` | Verificar que variable existe en Railway |
| `JSON inválido` | Asegurar que todo esté en una sola línea, sin saltos |
| `Permission denied` | Compartir carpeta en Drive con `railway-finnegans-sync@...` |
| `File not found` | Verificar que IDs de archivo son correctos |
| Ollama errors en logs | Agregar `DISABLE_AI=true` |

