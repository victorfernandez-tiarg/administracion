# ✅ CHECKLIST DE IMPLEMENTACIÓN - PASOS 5 & 6

## 📋 Pre-Validación Local

Antes de pushear a GitHub:

### Código & Archivos
- [ ] Ejecutar: `python validar_deploy.py`
  - [ ] Todos los archivos requeridos existen
  - [ ] Importaciones de Python funcionan
  - [ ] requirements.txt tiene dependencias de Google
  - [ ] .gitignore excluye .secrets/
  - [ ] Dockerfile sin curl

### Testing Local (Opcional pero Recomendado)
- [ ] Instalar dependencias: `pip install -r requirements.txt`
- [ ] Crear archivo `.secrets/sa.json` con JSON del SA (testing local)
- [ ] Configurar variables locales:
  ```bash
  $env:GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
  $env:GOOGLE_DRIVE_FACTURACION_FILE_ID='1299321983'
  $env:GOOGLE_DRIVE_CC_FILE_ID='257513436'
  ```
- [ ] Correr: `python etl/sync_drive.py` → debe descargar archivos o mostrar error claro
- [ ] Correr: `streamlit run dashboard/app.py` → app debe cargar sin errores
- [ ] Clickear botón "⬇️ Sincronizar Drive" → debe mostrar ✓ o mensaje de error

---

## 🚀 Push a GitHub

Una vez validado localmente:

```bash
cd ~/Documents/SEBAS/finnegans_bi/finnegans_bi

# 1. Verificar que .gitignore excluye .secrets/
ls -la .secrets/  # No debe mostrar JSON (si existe, debe estar ignorado)

# 2. Hacer commit
git add -A
git commit -m "Paso 5-6: Implementación de sincronización con Google Drive

- Nuevo módulo etl/sync_drive.py para descargas desde Drive
- Integración con procesar.py y procesar_cc.py
- Botón 'Sincronizar Drive' en sidebar
- Variables de entorno documentadas
- Dockerfile con healthcheck Python-based
- .gitignore actualizado para seguridad"

# 3. Push
git push origin main
```

- [ ] Commit pusheado exitosamente
- [ ] Verificar en GitHub que archivos están en main branch

---

## ⚙️ Configuración en Railway

### Prerequisitos
- [ ] JSON del Service Account descargado
- [ ] JSON minificado a una línea (sin saltos)
- [ ] Acceso a https://railway.app

### Pasos en Railway Dashboard

1. **Seleccionar Proyecto**:
   - [ ] Ir a https://railway.app
   - [ ] Seleccionar proyecto "finnegans_bi"

2. **Agregar Variables** (Variables tab):
   
   **Variable 1**:
   - [ ] Name: `GOOGLE_SERVICE_ACCOUNT_JSON`
   - [ ] Value: [JSON minificado - UNA LÍNEA]
   - [ ] Save

   **Variable 2**:
   - [ ] Name: `GOOGLE_DRIVE_FACTURACION_FILE_ID`
   - [ ] Value: `1299321983`
   - [ ] Save

   **Variable 3**:
   - [ ] Name: `GOOGLE_DRIVE_CC_FILE_ID`
   - [ ] Value: `257513436`
   - [ ] Save

   **Variable 4**:
   - [ ] Name: `DISABLE_AI`
   - [ ] Value: `true`
   - [ ] Save

3. **Esperar Redeploy**:
   - [ ] Railway redeplegará automáticamente
   - [ ] En "Deployments" → estado "success" (verde ✓)
   - [ ] Puede tardar 2-5 minutos

---

## 🔍 Validación en Producción

Una vez redeplegado:

### Verificar Logs
- [ ] En Railway → Logs tab
- [ ] Buscar: "Sincronizando archivos desde Google Drive"
- [ ] Si aparece → ✓ Sincronización se ejecutó
- [ ] Si ve error "Permission denied" → revisar compartir en Drive

### Verificar URL
- [ ] En Railway → Settings → Domain
- [ ] Copiar URL (ej: https://finnegans-bi-prod.up.railway.app)
- [ ] Abrir en navegador
- [ ] Esperar a que cargue Streamlit (10-30 seg primera vez)

### Testing en App
- [ ] Sidebar → Botón "⬇️ Sincronizar Drive"
  - [ ] Clickear → Esperar 5-10 segundos
  - [ ] Debe mostrar "✓ Sincronización completada"
  - [ ] Si muestra error → revisar logs en Railway

- [ ] Sidebar → Botón "🔄 Facturación"
  - [ ] Clickear → Esperar procesamiento
  - [ ] Tab "Facturación" → debe mostrar datos
  - [ ] Verificar que montos coinciden con Drive

- [ ] Sidebar → Botón "🔄 Ctas. Ctes."
  - [ ] Clickear → Esperar procesamiento
  - [ ] Tab "Cuentas Corrientes" → debe mostrar deudores
  - [ ] Verificar que saldos coinciden con Drive

### Verificar Datos
- [ ] Comparar datos en app con datos en Google Drive
- [ ] Facturación: algunos clientes con montos importantes deben verse
- [ ] CC: clientes en "+90 días" deben estar destacados en rojo

---

## 🛠️ Troubleshooting - Si algo Falla

### Problema: "JSON invalid" en logs
**Solución**:
- [ ] JSON tiene saltos de línea
- [ ] Minificar nuevamente usando herramienta online
- [ ] Verificar que empieza con `{` y termina con `}`
- [ ] Actualizar variable en Railway

### Problema: "Permission denied" descargando archivos
**Solución**:
- [ ] En Google Drive, compartir carpeta "Finnegans_BI" con:
  - [ ] Email: `railway-finnegans-sync@finnegans-bi.iam.gserviceaccount.com`
  - [ ] Permiso: "Viewer" (solo lectura)
- [ ] Esperar 30-60 segundos
- [ ] Reintentar sincronización

### Problema: "File not found" (404)
**Solución**:
- [ ] Verificar IDs en Google Drive URLs:
  - [ ] Facturación: debe ser `1299321983`
  - [ ] CC: debe ser `257513436`
- [ ] Si IDs son otros, actualizar variables en Railway

### Problema: App tarda mucho o timeout
**Solución**:
- [ ] Streamlit puede tardar 30-60 seg primera vez (normal)
- [ ] Revisar logs en Railway por errores
- [ ] Si Ollama error → ya configurado DISABLE_AI=true

### Problema: Datos no se actualizan
**Solución**:
- [ ] Verificar que botón "Sincronizar Drive" funciona (muestra ✓)
- [ ] Revisar "Última actualización" en sidebar
- [ ] Si no cambia → es que sincronización no corrió
- [ ] Revisar logs en Railway para errores

---

## 📊 Validación Final

Una vez todo funciona:

- [ ] ✓ URL de Railway accesible
- [ ] ✓ Botón "Sincronizar Drive" funciona
- [ ] ✓ Datos en "Facturación" están actualizados
- [ ] ✓ Datos en "Cuentas Corrientes" muestran deudores reales
- [ ] ✓ "+90 días" en rojo visible
- [ ] ✓ No hay errores en logs de Railway

---

## 🎉 Lanzamiento a Equipo

Una vez validado:

1. **Notificar a Equipo de Cobranza**:
   - URL de producción
   - Botón "Sincronizar Drive" antes de usar
   - Datos se actualizan cada vez que sincroniza

2. **Documentación**:
   - [ ] Compartir `RAILWAY_QUICK_START.md` con equipo
   - [ ] Explicar que datos son reales (Drive conectado)
   - [ ] Deudas en "+90 días" son prioritarias

3. **Monitoreo**:
   - [ ] Cada día, verificar que app está activa
   - [ ] Si falla, revisar logs en Railway
   - [ ] Contactar para troubleshooting

---

## 📝 Notas

- **Seguridad**: JSON del SA nunca está en repo gracias a .gitignore
- **Escalabilidad**: Agregar más archivos a Drive es fácil (solo agregar en `sync_drive.py`)
- **Resilencia**: Si Drive falla, app continúa con datos locales
- **Performance**: Sincronización toma 2-5 segundos

---

## ¿Falta Algo?

Si después de deployar necesitas:

- [ ] Sincronización automática cada N horas
- [ ] Webhooks desde Drive (sync inmediato)
- [ ] Historial de cambios
- [ ] Alertas por email si sync falla
- [ ] Dashboard de status de sync
- [ ] Validación/deduplicación más avanzada

**Avísame y lo implemento**.

---

**Estado**: 🟢 LISTO PARA IMPLEMENTAR EN RAILWAY

Cualquier problema, revisar esta checklist y `RAILWAY_QUICK_START.md`.

