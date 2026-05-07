"""
ETL — Finnegans BI
Transforma el .xlsx exportado de Finnegans GO en datos limpios para el dashboard.

Columnas reales del export de Finnegans GO (hoja1):
  Documento, Fecha, Comprobante, Cliente, Gravado, No gravado,
  Iva por tasa impositiva, Moneda, Importe mon. principal,
  Condición pago, Producto, Descripción item, Dim. valor, Imp. usd,
  Año - mes, Descripción, Empresa, Nivel 1 dimensión,
  Importenetopendiente, Cantidadesagro, Motivodeanulacion,
  Conceptoorganizacionnombre, Conceptoorganizacioncodigo,
  Domicilio, Solicitante, Situacion

Uso:
    python etl/procesar.py
"""

import pandas as pd
import os
from pathlib import Path
from datetime import datetime
import json
import warnings

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
    category=UserWarning,
)

RAW_DIR       = Path("data/raw")
PROCESSED_DIR = Path("data/processed")

NOTAS_CREDITO = [
    "Nota de Crédito de Ventas Electrónica",
    "FCE Nota de Crédito de Ventas Electrónica MIPymes",
]

MAPA_MONEDA = {
    "Pesos":   "ARS",
    "Dólares": "USD",
    "Dollars": "USD",
}

MAPA_EMPRESA = {
    "TIARG S.A.": "Local",
    "TIARG LLC":  "Internacional",
}


def _drive_sync_habilitado(sync_drive) -> bool:
    if sync_drive is not None:
        return bool(sync_drive)
    return os.getenv("AUTO_SYNC_DRIVE", "true").strip().lower() in {"1", "true", "yes", "si"}


def _sincronizar_si_corresponde(sync_drive):
    if not _drive_sync_habilitado(sync_drive):
        return
    from etl.sync_drive import sincronizar
    sincronizar()


def procesar_facturas() -> pd.DataFrame:
    path = RAW_DIR / "datos_facturacion.xlsx"
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró {path}. "
            "Exportá el reporte desde Finnegans GO y guardalo en data/raw/datos_facturacion.xlsx"
        )

    xls = pd.ExcelFile(path)
    nombres = {s.lower(): s for s in xls.sheet_names}
    sheet = nombres.get("hoja1", xls.sheet_names[0])
    df = pd.read_excel(path, sheet_name=sheet)

    df["Fecha"] = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")

    for col in ["Gravado", "No gravado", "Iva por tasa impositiva",
                "Importe mon. principal", "Imp. usd", "Importenetopendiente"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Cliente"]           = df["Cliente"].str.strip().str.title()
    df["Empresa"]           = df["Empresa"].str.strip()
    df["Moneda"]            = df["Moneda"].str.strip()
    df["Documento"]         = df["Documento"].str.strip()
    df["Nivel 1 dimensión"] = df["Nivel 1 dimensión"].str.strip()

    df["moneda_iso"]      = df["Moneda"].map(MAPA_MONEDA).fillna(df["Moneda"])
    df["razon_social"]    = df["Empresa"].map(MAPA_EMPRESA).fillna(df["Empresa"])
    df["es_nota_credito"] = df["Documento"].isin(NOTAS_CREDITO)

    df["monto_total_ars"] = df["Importe mon. principal"] 
    df["monto_neto_ars"]  = df["Gravado"] + df["No gravado"]
    df["monto_usd"]       = df["Imp. usd"]

    df["año"]        = df["Fecha"].dt.year
    df["mes"]        = df["Fecha"].dt.month
    df["mes_nombre"] = df["Fecha"].dt.strftime("%b %Y")

    df["linea_negocio"] = df["Nivel 1 dimensión"].str.replace(r"^\d+_", "", regex=True)

    df = df.rename(columns={
        "Fecha":               "fecha",
        "Comprobante":         "numero_comprobante",
        "Cliente":             "cliente",
        "Empresa":             "empresa",
        "Condición pago":      "condicion_pago",
        "Producto":            "producto",
        "Descripción item":    "descripcion_item",
        "Descripción":         "descripcion",
        "Nivel 1 dimensión":   "nivel_dimension",
        "Documento":           "tipo_documento",
        "Situacion":           "situacion",
        "Importenetopendiente":"importe_pendiente",
        "Dim. valor":          "dim_valor",
        "Cantidadesagro":      "cantidad",
    })

    # Asegurar que numero_comprobante sea string para evitar conflictos de tipo en parquet
    df["numero_comprobante"] = df["numero_comprobante"].astype(str)
    
    return df


def calcular_resumen_clientes(df: pd.DataFrame) -> pd.DataFrame:
    fact = df[~df["es_nota_credito"]].copy()

    ars = (
        fact[fact["moneda_iso"] == "ARS"]
        .groupby(["cliente", "razon_social"])
        .agg(
            facturado_ars=("monto_total_ars", "sum"),
            pendiente_ars=("importe_pendiente", "sum"),
            cantidad_fact=("numero_comprobante", "count"),
        )
        .reset_index()
    )

    usd = (
        fact[fact["moneda_iso"] == "USD"]
        .groupby(["cliente", "razon_social"])
        .agg(
            facturado_usd=("monto_usd", "sum"),
            pendiente_usd=("importe_pendiente", "sum"),
        )
        .reset_index()
    )

    resumen = ars.merge(usd, on=["cliente", "razon_social"], how="outer").fillna(0)
    return resumen


def guardar(df: pd.DataFrame, nombre: str):
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED_DIR / f"{nombre}.parquet", index=False)
    print(f"  ✓ {nombre}.parquet guardado ({len(df)} filas)")


def correr_etl(sync_drive: bool | None = None):
    print("─" * 40)
    print("Corriendo ETL Finnegans BI...")
    
    # Sincronizar archivos desde Google Drive
    if _drive_sync_habilitado(sync_drive):
        try:
            _sincronizar_si_corresponde(sync_drive)
        except Exception as e:
            print(f"  ⚠ Sincronización con Drive fallida (continuando con archivos locales): {e}")
    
    facturas = None
    try:
        facturas = procesar_facturas()
        guardar(facturas, "facturas")
        resumen = calcular_resumen_clientes(facturas)
        guardar(resumen, "resumen_clientes")
        meta = {"ultima_actualizacion": datetime.now().isoformat(), "filas": len(facturas)}
        with open(PROCESSED_DIR / "meta.json", "w") as f:
            json.dump(meta, f)
        print(f"ETL finalizado. {len(facturas)} registros procesados.")
    except FileNotFoundError as e:
        print(f"  ✗ {e}")
    except Exception as e:
        print(f"  ✗ Error ETL facturación: {e}")
    print("─" * 40)
    return facturas


if __name__ == "__main__":
    correr_etl()
