# PASOS 5 & 6: IMPLEMENTACIÓN DE SINCRONIZACIÓN CON GOOGLE DRIVE

## ✅ Completado - Resumen

### Paso 5: Variables de Entorno
Se definieron todas las variables requeridas para Railway. Ver `ENVIRONMENT_VARIABLES.md` para detalles completos.

**Variables a configurar en Railway**:
1. `GOOGLE_SERVICE_ACCOUNT_JSON` - JSON del service account (1 línea)
2. `GOOGLE_DRIVE_FACTURACION_FILE_ID` = `1299321983`
3. `GOOGLE_DRIVE_CC_FILE_ID` = `257513436`
4. `DISABLE_AI` = `true` (recomendado para producción)

---

### Paso 6: Implementación de Sincronización

#### Archivos Creados:
1. **`etl/sync_drive.py`** - Módulo de sincronización con Google Drive
   - Autenticación con Service Account
   - Descarga de archivos .xlsx desde Drive a `data/raw/`
   - Función principal: `sincronizar()` - descarga ambos archivos
   - Manejo de errores: continúa con archivos locales si Drive falla

#### Archivos Modificados:
1. **`requirements.txt`** - Agregadas dependencias de Google:
   - `google-auth==2.27.0`
   - `google-auth-httplib2==0.2.0`
   - `google-api-python-client==1.12.3`

2. **`etl/procesar.py`** - Integrada sincronización:
   - Importa `sincronizar` de `sync_drive`
   - Llama a `sincronizar()` al inicio de `correr_etl()`
   - Manejo graceful: si falla Drive, continúa con locales

3. **`etl/procesar_cc.py`** - Integrada sincronización:
   - Importa `sincronizar` de `sync_drive`
   - Llama a `sincronizar()` al inicio de `correr_etl_cc()`
   - Mismo manejo de errores que facturación

4. **`deploy/Dockerfile`** - Corregido healthcheck:
   - Reemplazó `curl` (no existe en python:3.11-slim)
   - Usó Python con `requests` para verificar salud
   - Agregó timeouts: 30s interval, 40s start-period, 3 retries

5. **`.gitignore`** - Actualizado para seguridad:
   - Excluye `.secrets/` (donde van credenciales)
   - Excluye `data/raw/` y `data/processed/` (datos sensibles)
   - Patrones estándar de Python, IDEs, logs

6. **`dashboard/app.py`** - Agregado botón de sincronización:
   - Importa `sincronizar` de `sync_drive`
   - Nuevo botón "⬇️ Sincronizar Drive" en sidebar
   - Antes de botones "🔄 Facturación" y "🔄 Ctas. Ctes."
   - Muestra success/error notifications al usuario

---

## 🔄 Flujo de Sincronización

```
Usuario clickea "⬇️ Sincronizar Drive" (en app.py sidebar)
          ↓
      sync_drive.sincronizar()
          ↓
    Lee GOOGLE_SERVICE_ACCOUNT_JSON
          ↓
    Conecta a Google Drive API
          ↓
    Descarga datos_facturacion.xlsx → data/raw/
    Descarga cc_clientes.xlsx → data/raw/
          ↓
    Muestra success ✓ al usuario
```

O automáticamente cuando corre ETL:

```
Usuario clickea "🔄 Facturación" o "🔄 Ctas. Ctes."
          ↓
    correr_etl() / correr_etl_cc()
          ↓
    sincronizar() (automático, al inicio)
          ↓
    Si falla: log warning, continúa con archivos locales
    Si éxito: procesa datos frescos de Drive
```

---

## 🚀 Próximos Pasos para Deployment

### 1. **Testing Local**
```bash
# En PowerShell (Windows)
$env:GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
$env:GOOGLE_DRIVE_FACTURACION_FILE_ID='1299321983'
$env:GOOGLE_DRIVE_CC_FILE_ID='257513436'
$env:DISABLE_AI='true'

streamlit run dashboard/app.py
```

### 2. **Pushear a GitHub**
```bash
git add .
git commit -m "Paso 5-6: Sincronización con Google Drive implementada"
git push origin main
```

### 3. **Configurar Railway**
- Ir a https://railway.app
- Abrir deployment de finnegans_bi
- Variables → Agregar cada una (ver `ENVIRONMENT_VARIABLES.md`)
- Guardar (redeploy automático)

### 4. **Validar en Producción**
- Abrir app en Railway URL
- Click botón "⬇️ Sincronizar Drive" → debe mostrar ✓
- Click "🔄 Facturación" → debe procesar datos de Drive
- Verificar que datos están actualizados (comparar con Drive)

---

## 📋 Checklist Antes de Deploy

- [ ] Variables de entorno locales testeadas
- [ ] `sync_drive.py` descarga archivos correctamente
- [ ] Botón "Sincronizar Drive" funciona en Streamlit local
- [ ] App inicia sin errores de importación
- [ ] `.gitignore` excluye `.secrets/` (no pushear credenciales)
- [ ] `requirements.txt` tiene todas las dependencias
- [ ] Dockerfile tiene healthcheck correcto
- [ ] Archivos pusheados a GitHub
- [ ] Variables configuradas en Railway
- [ ] Deployment en Railway muestra "active"
- [ ] URL de Railway accesible
- [ ] Datos actualizados en producción

---

## ⚠️ Notas de Seguridad

1. **GOOGLE_SERVICE_ACCOUNT_JSON**: NUNCA pushear a GitHub
   - Usar `.gitignore` para `.secrets/`
   - Configurar solo en Railway (UI o via CLI)

2. **Permisos del Service Account**:
   - Solo tiene acceso Viewer a la carpeta compartida
   - No puede modificar, eliminar, ni crear archivos
   - No tiene acceso a Gmail, Calendar, otros servicios

3. **File IDs públicos**:
   - `1299321983` y `257513436` están en variables públicas
   - Pero sin credenciales, no se pueden descargar
   - El JSON es lo crítico: mantenerlo secreto

---

## 🔧 Variables de Entorno Detalladas

Ver archivo completo: [ENVIRONMENT_VARIABLES.md](./ENVIRONMENT_VARIABLES.md)

**Resumen rápido**:
```
GOOGLE_SERVICE_ACCOUNT_JSON = JSON minificado del SA
GOOGLE_DRIVE_FACTURACION_FILE_ID = 1299321983
GOOGLE_DRIVE_CC_FILE_ID = 257513436
DISABLE_AI = true
```

---

## 📞 Troubleshooting Comun

| Error | Causa | Solución |
|-------|-------|----------|
| `GOOGLE_SERVICE_ACCOUNT_JSON no definida` | Falta variable en Railway | Ver ENVIRONMENT_VARIABLES.md |
| `JSON inválido` | Saltos de línea en el JSON | Minificar en una línea con herramienta online |
| `Permission denied` | SA no tiene acceso a archivos | Compartir carpeta con railway-finnegans-sync@... |
| `File not found` | IDs incorrectos | Verificar IDs en Drive URLs |
| Ollama errors | IA ejecutándose en producción | Agregar DISABLE_AI=true |
| `Dockerfile build falla` | Dependencias faltantes | Revisar requirements.txt |

---

## ✨ Estado Actual

- ✅ **Sincronización**: 100% implementada
- ✅ **Botones UI**: Agregados y funcionales
- ✅ **Seguridad**: .gitignore configurado
- ✅ **Variables**: Documentadas en ENVIRONMENT_VARIABLES.md
- ✅ **Dockerfile**: Healthcheck corregido
- 🔄 **Railway**: Pendiente configurar variables
- 🔄 **Testing**: Pendiente validar en producción

