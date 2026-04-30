# 📊 Finnegans BI — Dashboard de Facturación y Cuentas Corrientes

Stack: Python · pandas · Streamlit · Plotly · SQLite · Render/Railway

---

## Estructura del proyecto

```
finnegans_bi/
├── data/
│   ├── raw/          ← Acá van los .xlsx exportados de Finnegans GO
│   └── processed/    ← Generado automáticamente por el ETL
├── etl/
│   └── procesar.py   ← Script de transformación de datos
├── dashboard/
│   └── app.py        ← App Streamlit (el dashboard)
├── deploy/
│   ├── Dockerfile
│   └── render.yaml
├── requirements.txt
└── README.md
```

---

## Flujo de trabajo (el día a día)

1. Exportar desde Finnegans GO:
   - Facturas de ventas → guardar como `data/raw/facturas.xlsx`
   - Cuentas corrientes → guardar como `data/raw/cuentas_corrientes.xlsx`

2. En el dashboard, apretar el botón **"🔄 Actualizar datos"**
   (o correr `python etl/procesar.py` desde la terminal)

3. Listo — todos los usuarios ven los datos frescos

---

## Instalación local (primera vez)

```bash
# Clonar / descomprimir el proyecto
cd finnegans_bi

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate       # Mac/Linux
.venv\Scripts\activate          # Windows

# Instalar dependencias
pip install -r requirements.txt

# Correr el dashboard
streamlit run dashboard/app.py
```

Abre automáticamente en http://localhost:8501

---

## Deploy en Render (producción)

Ver instrucciones en `deploy/README_deploy.md`

---

## Columnas esperadas en los .xlsx

### facturas.xlsx
| Columna | Descripción |
|---|---|
| numero_factura | ID único de la factura |
| fecha | Fecha de emisión |
| cliente | Nombre del cliente |
| razon_social | "Local" o "Internacional" |
| moneda | ARS o USD |
| monto_neto | Monto sin impuestos |
| monto_total | Monto con impuestos |
| estado | Emitida / Anulada / etc. |

### cuentas_corrientes.xlsx
| Columna | Descripción |
|---|---|
| cliente | Nombre del cliente |
| razon_social | "Local" o "Internacional" |
| fecha_vencimiento | Fecha de vencimiento |
| monto | Monto de la deuda |
| moneda | ARS o USD |
| dias_vencido | Calculado automáticamente |

> Si los nombres de columna difieren, editar el mapeo en `etl/procesar.py` (sección CONFIGURACIÓN)
