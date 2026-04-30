"""
ETL — Cuentas Corrientes de Clientes (Finnegans GO)
Lógica contable:
  Debe ppal  = cargos (facturas)
  Haber ppal = cobros y notas de crédito
  Saldo ppal = saldo acumulado. El ÚLTIMO valor por cliente = deuda real actual.
"""

import pandas as pd
from pathlib import Path
from datetime import date
import json
from etl.sync_drive import sincronizar

RAW_DIR       = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

PREFIJOS_COBRO = ["COBRANZA", "COBRANZA_FCE", "NCVEE", "FCEVCTA", "FCEINCVTAELEC", "FCENCVTAELEC"]


def tipo_movimiento(doc: str) -> str:
    if not doc or doc.strip() in ("", "Saldo Inicial"):
        return "Saldo Inicial"
    pref = doc.split(" - ")[0].strip().upper()
    if any(pref.startswith(p) for p in PREFIJOS_COBRO):
        return "Cobro/NC"
    return "Factura/Cargo"


def calcular_aging(dias: float) -> str:
    if dias <= 0:   return "Al día"
    if dias <= 30:  return "1–30 días"
    if dias <= 60:  return "31–60 días"
    if dias <= 90:  return "61–90 días"
    return "+90 días"


def procesar_cc() -> tuple:
    path = RAW_DIR / "cc_clientes.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"No se encontró {path}")

    xls = pd.ExcelFile(path)
    nombres = {s.lower(): s for s in xls.sheet_names}
    sheet = nombres.get("hoja1", xls.sheet_names[0])
    df = pd.read_excel(path, sheet_name=sheet)

    # Tipos
    df["Fecha"]             = pd.to_datetime(df["Fecha"],             errors="coerce")
    df["Fecha vencimiento"] = pd.to_datetime(df["Fecha vencimiento"], errors="coerce")
    for col in ["Debe ppal", "Haber ppal", "Saldo ppal", "Cotizacionmonedasecundaria"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Cliente"]    = df["Cliente"].str.strip().str.title()
    df["Documento"]  = df["Documento"].fillna("").str.strip()
    df["Descripción"] = df["Descripción"].fillna("")
    df["tipo"]       = df["Documento"].apply(tipo_movimiento)

    hoy = pd.Timestamp(date.today())

    # Saldo real = último registro por cliente
    idx_ultimo = df.groupby("Cliente")["Fecha"].idxmax()
    saldos = df.loc[idx_ultimo, ["Cliente", "Saldo ppal"]].rename(
        columns={"Saldo ppal": "saldo_actual"}
    ).copy()

    # Vencimiento más antiguo con saldo pendiente
    pend = df[(df["tipo"] == "Factura/Cargo") & (df["Saldo ppal"] > 0)]
    if not pend.empty:
        primera = (
            pend.sort_values("Fecha vencimiento")
            .groupby("Cliente")
            .first()
            .reset_index()[["Cliente", "Fecha vencimiento"]]
            .rename(columns={"Fecha vencimiento": "venc"})
        )
    else:
        primera = pd.DataFrame(columns=["Cliente", "venc"])

    saldos = saldos.merge(primera, on="Cliente", how="left")
    saldos["venc"]         = saldos["venc"].fillna(hoy)
    saldos["dias_vencido"] = (hoy - saldos["venc"]).dt.days.clip(lower=0)
    saldos["aging"]        = saldos["dias_vencido"].apply(calcular_aging)

    # Totales históricos por cliente
    totales = (
        df.groupby("Cliente")
        .agg(total_facturado=("Debe ppal", "sum"), total_cobrado=("Haber ppal", "sum"))
        .reset_index()
    )
    saldos = saldos.merge(totales, on="Cliente", how="left")
    saldos["ratio_cobranza"] = (
        saldos["total_cobrado"] / saldos["total_facturado"].replace(0, 1) * 100
    ).round(1)

    # Solo deudores reales
    saldos = saldos[saldos["saldo_actual"] > 0].sort_values(
        "saldo_actual", ascending=False
    ).reset_index(drop=True)

    return df, saldos


def guardar_csv(df: pd.DataFrame, nombre: str):
    """Guarda como parquet si pyarrow disponible, sino CSV."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(PROCESSED_DIR / f"{nombre}.parquet", index=False)
        print(f"  ✓ {nombre}.parquet ({len(df)} filas)")
    except ImportError:
        df.to_csv(PROCESSED_DIR / f"{nombre}.csv", index=False)
        print(f"  ✓ {nombre}.csv ({len(df)} filas)")


def correr_etl_cc(sync_drive: bool = True):
    print("Procesando cuentas corrientes...")
    
    # Sincronizar archivos desde Google Drive
    if sync_drive:
        try:
            sincronizar()
        except Exception as e:
            print(f"  ⚠ Sincronización con Drive fallida (continuando con archivos locales): {e}")
    
    try:
        movimientos, saldos = procesar_cc()
        guardar_csv(movimientos, "cc_movimientos")
        guardar_csv(saldos, "cc_saldos")
        print(f"  → {len(saldos)} clientes con saldo pendiente")
        print(f"  → Deuda total: ${saldos['saldo_actual'].sum():,.0f}")
        return movimientos, saldos
    except FileNotFoundError as e:
        print(f"  ✗ {e}")
        return None, None
    except Exception as e:
        print(f"  ✗ Error ETL cuentas corrientes: {e}")
        return None, None


if __name__ == "__main__":
    correr_etl_cc()
