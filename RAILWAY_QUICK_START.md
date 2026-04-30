# RAILWAY DEPLOYMENT - GUÍA RÁPIDA

## Paso 1: Preparar credenciales (5 minutos)

### Obtener JSON del Service Account
1. Ir a Google Cloud Console: https://console.cloud.google.com/
2. Seleccionar proyecto: **finnegans-bi**
3. Ir a "IAM y administración" → "Cuentas de servicio"
4. Click en `railway-finnegans-sync@finnegans-bi.iam.gserviceaccount.com`
5. Tab "Claves"
6. Click "Agregar clave" → "JSON" → se descarga automáticamente

### Minificar JSON a una línea
**Opción 1 (Python):**
```bash
python -c "import json; data=json.load(open('ruta/al/archivo.json')); print(json.dumps(data))"
```

**Opción 2 (Online):**
- Ir a: https://jsoncrush.com/ o https://tools.knightrider.digital/json-minifier/
- Copiar JSON descargado
- Pegar, convertir, copiar resultado

---

## Paso 2: Configurar variables en Railway (10 minutos)

### En Railway Dashboard:
1. Ir a: https://railway.app
2. Loggearse con GitHub
3. Seleccionar proyecto: **finnegans_bi**
4. Click en "Variables" (o "Environment Variables")
5. Agregar 4 variables:

#### Variable 1: GOOGLE_SERVICE_ACCOUNT_JSON
- **Name**: `GOOGLE_SERVICE_ACCOUNT_JSON`
- **Value**: Pegar el JSON minificado (UNA SOLA LÍNEA)
- Click "Save"

#### Variable 2: GOOGLE_DRIVE_FACTURACION_FILE_ID
- **Name**: `GOOGLE_DRIVE_FACTURACION_FILE_ID`
- **Value**: `1299321983`
- Click "Save"

#### Variable 3: GOOGLE_DRIVE_CC_FILE_ID
- **Name**: `GOOGLE_DRIVE_CC_FILE_ID`
- **Value**: `257513436`
- Click "Save"

#### Variable 4: DISABLE_AI
- **Name**: `DISABLE_AI`
- **Value**: `true`
- Click "Save"

### Resultado esperado:
- Railway redeplegará automáticamente
- En la sección "Deployments", verás una nueva compilación en progreso
- Esperar a que termine (status: "success" o ✓ verde)

---

## Paso 3: Testing (5 minutos)

### Verificar logs en Railway:
1. En Railway, click en "Logs"
2. Buscar mensajes:
   ```
   "Sincronizando archivos desde Google Drive..."
   "✓ datos_facturacion.xlsx sincronizado"
   "✓ cc_clientes.xlsx sincronizado"
   ```
   - Si ves esto → ✅ Sincronización funciona

### Verificar URL de Railway:
1. En Railway, ir a "Settings"
2. Copiar URL (ej: `https://finnegans-bi-prod.up.railway.app`)
3. Abrir URL en navegador
4. Esperar a que cargue Streamlit (puede tardar 10-30 seg la primera vez)

### Pruebas en la app:
1. **Botón "⬇️ Sincronizar Drive"**:
   - Click → debe mostrar "✓ Sincronización completada"
   - Si falla → check logs en Railway

2. **Botón "🔄 Facturación"**:
   - Click → procesa datos de Drive
   - Esperar a que termine
   - Verificar que Tab "Facturación" muestra datos actuales

3. **Botón "🔄 Ctas. Ctes."**:
   - Click → procesa CC de Drive
   - Verificar Tab "Cuentas Corrientes" con datos nuevos

---

## Checklist Final

- [ ] JSON del Service Account descargado
- [ ] JSON minificado a una línea
- [ ] 4 variables configuradas en Railway
- [ ] Railway en estado "success" (redeploy completado)
- [ ] App accesible por URL
- [ ] Botón "Sincronizar Drive" clickeable
- [ ] Datos en Tabs actualizados

---

## Troubleshooting Rápido

### "Variable not found" error en logs
→ Verificar que nombre de variable es exacto (case-sensitive)

### "JSON invalid" error
→ JSON tiene saltos de línea. Minificar en una línea

### "Permission denied" descargando archivos
→ Service Account no tiene acceso. En Google Drive:
1. Click derecho en carpeta "Finnegans_BI"
2. "Compartir"
3. Agregar email: `railway-finnegans-sync@finnegans-bi.iam.gserviceaccount.com`
4. Permiso: "Viewer"

### "File not found"
→ IDs incorrectos. Verificar:
- Facturación: debe ser `1299321983`
- CC: debe ser `257513436`

### Timeout o "app is slow"
→ Primera carga puede tardar 30-60 seg. Normal en Railway con spin-down.

---

## ¿Qué sigue?

Una vez confirmado en Railway:
1. ✅ Dashboard en producción
2. ✅ Datos sincronizados automáticamente
3. ✅ Botón manual "Sincronizar Drive" disponible
4. ✅ Equipo de cobranza puede usar desde cualquier lugar

**Próximas mejoras opcionales**:
- Agregar sincronización automática cada N horas (cron job)
- Alertas si sincronización falla
- Webhook desde Google Drive para sync inmediato
- Histórico de cambios en datos

---

## Contacto / Ayuda

Si algo no funciona:
1. Revisar logs en Railway (Settings → Logs)
2. Consultar `ENVIRONMENT_VARIABLES.md` para validar formato de variables
3. Revisar `DEPLOYMENT_STEPS.md` para contexto completo

