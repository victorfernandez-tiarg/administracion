"""
Genera datos de ejemplo para testear el dashboard
sin necesitar exportar de Finnegans GO.

Uso:
    python generar_datos_ejemplo.py
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import date, timedelta
import random

random.seed(42)
np.random.seed(42)

Path("data/raw").mkdir(parents=True, exist_ok=True)

CLIENTES_LOCAL = [
    "Empresa Alpha SA", "Beta Soluciones SRL", "Gamma Tech SA",
    "Delta Corp SA", "Epsilon Group SRL", "Zeta Sistemas SA",
    "Eta Consulting SRL", "Iota Digital SA",
]

CLIENTES_INT = [
    "Acme Corp", "Global Tech LLC", "Northern Systems Inc",
    "Pacific Solutions Ltd", "Atlantic Group Inc",
]

def fecha_aleatoria(inicio="2024-01-01", fin="2024-12-31"):
    d1 = date.fromisoformat(inicio)
    d2 = date.fromisoformat(fin)
    return d1 + timedelta(days=random.randint(0, (d2 - d1).days))


# ── FACTURAS ──────────────────────────────────────
filas = []
for i in range(1, 201):
    es_int = random.random() < 0.25
    cliente = random.choice(CLIENTES_INT if es_int else CLIENTES_LOCAL)
    moneda  = "USD" if es_int else "ARS"
    monto_neto = round(random.uniform(50_000, 800_000) if moneda == "ARS" else random.uniform(500, 8_000), 2)
    monto_total = round(monto_neto * 1.21, 2)
    estado = random.choices(["Emitida", "Anulada"], weights=[95, 5])[0]
    filas.append({
        "numero_factura": f"F-{i:04d}",
        "fecha": fecha_aleatoria(),
        "cliente": cliente,
        "razon_social": "Internacional" if es_int else "Local",
        "moneda": moneda,
        "monto_neto": monto_neto,
        "monto_total": monto_total,
        "estado": estado,
    })

pd.DataFrame(filas).to_excel("data/raw/facturas.xlsx", index=False)
print("✓ data/raw/facturas.xlsx generado")


# ── CUENTAS CORRIENTES ──────────────────────────
filas_cc = []
hoy = date.today()
for cliente in CLIENTES_LOCAL + CLIENTES_INT:
    es_int = cliente in CLIENTES_INT
    n_comprobantes = random.randint(1, 4)
    for _ in range(n_comprobantes):
        dias_atras = random.randint(-10, 120)
        venc = hoy - timedelta(days=dias_atras)
        moneda = "USD" if es_int else "ARS"
        monto = round(random.uniform(30_000, 500_000) if moneda == "ARS" else random.uniform(300, 5_000), 2)
        filas_cc.append({
            "cliente": cliente,
            "razon_social": "Internacional" if es_int else "Local",
            "fecha_vencimiento": venc,
            "monto": monto,
            "moneda": moneda,
        })

pd.DataFrame(filas_cc).to_excel("data/raw/cuentas_corrientes.xlsx", index=False)
print("✓ data/raw/cuentas_corrientes.xlsx generado")
print("\nAhora corrés: python etl/procesar.py")
