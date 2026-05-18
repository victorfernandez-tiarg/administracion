"""
ETL — Cuentas Corrientes de Clientes (Finnegans GO)
Lógica contable:
  Debe ppal  = cargos (facturas)
  Haber ppal = cobros y notas de crédito
  Saldo ppal = saldo acumulado. El ÚLTIMO valor por cliente = deuda real actual.
"""

import pandas as pd
import os
from pathlib import Path
from datetime import date
import warnings

from etl.procesar_composicion import cargar_composicion_saldos, normalizar_nombre_cliente
from etl.db import guardar

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
    category=UserWarning,
)

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


def _drive_sync_habilitado(sync_drive) -> bool:
    if sync_drive is not None:
        return bool(sync_drive)
    return os.getenv("AUTO_SYNC_DRIVE", "true").strip().lower() in {"1", "true", "yes", "si"}


def _sincronizar_si_corresponde(sync_drive):
    if not _drive_sync_habilitado(sync_drive):
        return
    from etl.sync_drive import sincronizar
    sincronizar()


def resumir_vencimientos(
    df: pd.DataFrame, saldos_actuales: pd.DataFrame, hoy: pd.Timestamp
) -> pd.DataFrame:
    cargos = df[(df["tipo"] == "Factura/Cargo") & (df["Cliente"].notna())].copy()
    cargos["importe_cargo"] = pd.to_numeric(cargos["Debe ppal"], errors="coerce").fillna(0)
    cargos = cargos[cargos["importe_cargo"] > 0].copy()
    cargos = cargos.rename(columns={"Fecha vencimiento": "fecha_vencimiento", "Fecha": "fecha_movimiento"})

    if cargos.empty:
        return pd.DataFrame(
            columns=[
                "Cliente",
                "saldo_pendiente_cc",
                "saldo_vencido",
                "saldo_por_vencer",
                "venc",
                "prox_vencimiento",
                "dias_vencido",
                "dias_vencido_max",
                "venc_referencia",
            ]
        )

    cargos = cargos[cargos["Cliente"].ne("")].copy()
    cargos["_fecha_venc_sort"] = cargos["fecha_vencimiento"].fillna(pd.Timestamp.min)
    cargos["_fecha_mov_sort"] = cargos["fecha_movimiento"].fillna(pd.Timestamp.min)

    resumen = []
    for fila in saldos_actuales[["Cliente", "saldo_actual"]].itertuples(index=False):
        cliente = fila.Cliente
        saldo_actual = max(float(fila.saldo_actual), 0)
        if saldo_actual <= 0:
            continue

        cargos_cliente = cargos[cargos["Cliente"] == cliente].sort_values(
            ["_fecha_venc_sort", "_fecha_mov_sort"],
            ascending=[False, False],
        )

        saldo_restante = saldo_actual
        abiertos = []
        for cargo in cargos_cliente.itertuples(index=False):
            if saldo_restante <= 0:
                break
            tramo_abierto = min(float(cargo.importe_cargo), saldo_restante)
            if tramo_abierto <= 0:
                continue
            saldo_restante -= tramo_abierto
            abiertos.append((cargo.fecha_vencimiento, tramo_abierto))

        saldo_vencido = 0.0
        saldo_por_vencer = saldo_actual
        prox_vencimiento = pd.NaT
        venc = pd.NaT
        dias_vencido = 0
        dias_vencido_max = 0

        if abiertos:
            vencidos = []
            proximos = []
            for fecha_vencimiento, monto_abierto in abiertos:
                if pd.isna(fecha_vencimiento):
                    proximos.append((fecha_vencimiento, monto_abierto, 0))
                    continue
                dias = int((hoy - fecha_vencimiento).days)
                if dias > 0:
                    vencidos.append((fecha_vencimiento, monto_abierto, dias))
                else:
                    proximos.append((fecha_vencimiento, monto_abierto, 0))

            if vencidos:
                saldo_vencido = float(sum(monto for _, monto, _ in vencidos))
                saldo_por_vencer = max(saldo_actual - saldo_vencido, 0)
                dias_vencido = int(round(
                    sum(monto * dias for _, monto, dias in vencidos) / saldo_vencido,
                    0,
                ))
                dias_vencido_max = int(max(dias for _, _, dias in vencidos))
                venc = min(fecha for fecha, _, _ in vencidos)
            if proximos:
                fechas_proximas = [fecha for fecha, _, _ in proximos if pd.notna(fecha)]
                prox_vencimiento = min(fechas_proximas) if fechas_proximas else pd.NaT

        resumen.append(
            {
                "Cliente": cliente,
                "saldo_pendiente_cc": saldo_actual,
                "saldo_vencido": saldo_vencido,
                "saldo_por_vencer": saldo_por_vencer,
                "venc": venc,
                "prox_vencimiento": prox_vencimiento,
                "dias_vencido": dias_vencido,
                "dias_vencido_max": dias_vencido_max,
                "venc_referencia": venc if pd.notna(venc) else prox_vencimiento,
            }
        )

    return pd.DataFrame(resumen)


def conciliar_saldos(df_mov: pd.DataFrame) -> pd.DataFrame:
    base = df_mov[df_mov["Cliente"].notna() & df_mov["Cliente"].ne("")].copy()
    if base.empty:
        return pd.DataFrame(columns=[
            "Cliente",
            "saldo_inicial",
            "debe_total",
            "haber_total",
            "saldo_reconstruido",
            "saldo_final_ledger",
            "dif_conciliacion",
            "conciliado",
        ])

    base["Debe ppal"] = pd.to_numeric(base["Debe ppal"], errors="coerce").fillna(0)
    base["Haber ppal"] = pd.to_numeric(base["Haber ppal"], errors="coerce").fillna(0)
    base["Saldo ppal"] = pd.to_numeric(base["Saldo ppal"], errors="coerce").fillna(0)
    base["_fecha_sort"] = base["Fecha"].fillna(pd.Timestamp.min)

    primeros = (
        base.sort_values(["Cliente", "_fecha_sort", "_orden_origen"])
        .groupby("Cliente", as_index=False)
        .head(1)
        [["Cliente", "Saldo ppal"]]
        .rename(columns={"Saldo ppal": "saldo_inicial"})
    )
    ultimos = (
        base.sort_values(["Cliente", "_fecha_sort", "_orden_origen"])
        .groupby("Cliente", as_index=False)
        .tail(1)
        [["Cliente", "Saldo ppal"]]
        .rename(columns={"Saldo ppal": "saldo_final_ledger"})
    )
    totales = (
        base.groupby("Cliente", as_index=False)
        .agg(debe_total=("Debe ppal", "sum"), haber_total=("Haber ppal", "sum"))
    )

    conc = primeros.merge(ultimos, on="Cliente", how="inner").merge(totales, on="Cliente", how="left")
    conc["saldo_reconstruido"] = conc["saldo_inicial"] + conc["debe_total"] - conc["haber_total"]
    conc["dif_conciliacion"] = conc["saldo_final_ledger"] - conc["saldo_reconstruido"]
    conc["conciliado"] = conc["dif_conciliacion"].abs() <= 1.0
    return conc


def procesar_cc() -> tuple:
    path = RAW_DIR / "cc_clientes.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"No se encontró {path}")

    xls = pd.ExcelFile(path)
    nombres = {s.lower(): s for s in xls.sheet_names}
    sheet = nombres.get("hoja1", xls.sheet_names[0])
    df = pd.read_excel(path, sheet_name=sheet)

    # Tipos
    df["Fecha"]             = pd.to_datetime(df["Fecha"], dayfirst=True, errors="coerce")
    df["Fecha vencimiento"] = pd.to_datetime(df["Fecha vencimiento"], dayfirst=True, errors="coerce")
    for col in ["Debe ppal", "Haber ppal", "Saldo ppal", "Cotizacionmonedasecundaria"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Cliente"]    = df["Cliente"].astype(str).str.strip().str.title()
    df["Documento"]  = df["Documento"].fillna("").astype(str).str.strip()
    if "Descripción" in df.columns:
        df["Descripción"] = df["Descripción"].fillna("")
    else:
        df["Descripción"] = ""
    df["tipo"]       = df["Documento"].apply(tipo_movimiento)

    hoy = pd.Timestamp(date.today())

    # Saldo real = último movimiento por cliente (misma fecha resuelta por orden de aparición)
    # Evita errores de idxmax cuando hay fechas repetidas, datos pegados desde Sheets o filas desordenadas.
    df_mov = df.reset_index().rename(columns={"index": "_orden_origen"})
    df_mov["_fecha_sort"] = df_mov["Fecha"].fillna(pd.Timestamp.min)
    ultimos = (
        df_mov[df_mov["Cliente"].notna() & df_mov["Cliente"].ne("")]
        .sort_values(["Cliente", "_fecha_sort", "_orden_origen"])
        .groupby("Cliente", as_index=False)
        .tail(1)
    )
    saldos = ultimos[["Cliente", "Saldo ppal"]].rename(
        columns={"Saldo ppal": "saldo_actual"}
    ).copy()

    conciliacion = conciliar_saldos(df_mov)
    saldos = saldos.merge(
        conciliacion[[
            "Cliente", "saldo_inicial", "debe_total", "haber_total",
            "saldo_reconstruido", "saldo_final_ledger", "dif_conciliacion", "conciliado"
        ]],
        on="Cliente",
        how="left",
    )

    resumen_venc = resumir_vencimientos(df, saldos, hoy)
    saldos = saldos.merge(resumen_venc, on="Cliente", how="left")
    saldos["saldo_pendiente_cc"] = saldos["saldo_pendiente_cc"].fillna(saldos["saldo_actual"])
    saldos["saldo_vencido"] = saldos["saldo_vencido"].fillna(0)
    saldos["saldo_por_vencer"] = saldos["saldo_por_vencer"].fillna(
        saldos["saldo_actual"] - saldos["saldo_vencido"]
    ).clip(lower=0)
    saldos["venc"] = saldos["venc_referencia"].fillna(hoy)
    saldos["dias_vencido"] = saldos["dias_vencido"].fillna(0).astype(int)
    saldos["dias_vencido_max"] = saldos["dias_vencido_max"].fillna(0).astype(int)
    saldos["fuente_aging"] = "cc_movimientos"

    composicion = cargar_composicion_saldos(hoy)
    if composicion is not None and not composicion.empty:
        saldos = saldos.merge(composicion, on="Cliente", how="left")
        tiene_comp = saldos["saldo_composicion"].fillna(0) > 0
        saldos.loc[tiene_comp, "saldo_vencido"] = saldos.loc[tiene_comp, "saldo_vencido_comp"].fillna(0)
        saldos.loc[tiene_comp, "saldo_por_vencer"] = saldos.loc[tiene_comp, "saldo_por_vencer_comp"].fillna(0)
        saldos.loc[tiene_comp, "dias_vencido"] = saldos.loc[tiene_comp, "dias_vencido_comp"].fillna(0).astype(int)
        saldos.loc[tiene_comp, "dias_vencido_max"] = saldos.loc[tiene_comp, "dias_vencido_max_comp"].fillna(0).astype(int)
        saldos.loc[tiene_comp, "venc"] = saldos.loc[tiene_comp, "venc_comp_min"].fillna(saldos.loc[tiene_comp, "venc"])
        saldos.loc[tiene_comp, "fuente_aging"] = "composicion"

        for col in [
            "saldo_composicion",
            "saldo_vencido_comp",
            "saldo_por_vencer_comp",
            "centro_costo_principal",
            "centros_costo",
        ]:
            if col not in saldos.columns:
                saldos[col] = None
    else:
        # Sin archivo de composición: derivar comprobantes pendientes desde movimientos
        comp_derivada = derivar_comprobantes_pendientes(df_mov, saldos, hoy)
        if not comp_derivada.empty:
            guardar(comp_derivada, "cc_composicion")
            print(f"  \u2192 cc_composicion derivado de movimientos: {len(comp_derivada)} comprobantes")
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
        ["saldo_vencido", "saldo_actual", "dias_vencido"],
        ascending=[False, False, False],
    ).reset_index(drop=True)

    return df, saldos


def derivar_comprobantes_pendientes(
    df_mov: pd.DataFrame, saldos: pd.DataFrame, hoy: pd.Timestamp
) -> pd.DataFrame:
    """
    Fallback cuando no existe archivo de composición de saldos:
    deriva los comprobantes pendientes directamente desde cc_clientes.xlsx.
    Aplica el saldo actual de cada cliente contra sus facturas más recientes (LIFO)
    para determinar qué facturas permanecen abiertas y las guarda como cc_composicion.
    """
    cols_necesarias = ["Cliente", "Documento", "Debe ppal", "tipo"]
    if any(c not in df_mov.columns for c in cols_necesarias):
        return pd.DataFrame()

    col_fv = "Fecha vencimiento" if "Fecha vencimiento" in df_mov.columns else None
    col_f  = "Fecha"             if "Fecha"             in df_mov.columns else None

    cargos = df_mov[df_mov["tipo"] == "Factura/Cargo"].copy()
    cargos = cargos[cargos["Cliente"].notna() & cargos["Cliente"].ne("")]
    cargos["_importe"] = pd.to_numeric(cargos["Debe ppal"], errors="coerce").fillna(0)
    cargos = cargos[cargos["_importe"] > 0].copy()
    cargos["_fecha_venc"] = pd.to_datetime(cargos[col_fv], errors="coerce") if col_fv else pd.NaT
    cargos["_fecha_mov"]  = pd.to_datetime(cargos[col_f],  errors="coerce") if col_f  else pd.NaT
    cargos["_fv_sort"] = cargos["_fecha_venc"].fillna(pd.Timestamp.min)
    cargos["_fm_sort"] = cargos["_fecha_mov"].fillna(pd.Timestamp.min)

    deudores = saldos[saldos["saldo_actual"] > 0][["Cliente", "saldo_actual"]]

    filas = []
    for cliente, saldo_actual in zip(deudores["Cliente"], deudores["saldo_actual"]):
        saldo_restante = max(float(saldo_actual), 0.0)
        if saldo_restante <= 0:
            continue

        cargos_cli = cargos[cargos["Cliente"] == cliente].sort_values(
            ["_fv_sort", "_fm_sort"], ascending=[False, False]
        )
        for _, row in cargos_cli.iterrows():
            if saldo_restante <= 0:
                break
            tramo = min(float(row["_importe"]), saldo_restante)
            if tramo <= 0:
                continue
            saldo_restante -= tramo
            fv = row["_fecha_venc"]
            dias = int((hoy - fv).days) if pd.notna(fv) else 0
            filas.append({
                "Cliente":           cliente,
                "cliente_norm":      normalizar_nombre_cliente(cliente),
                "centro_costo":      "Sin centro",
                "saldo_abierto":     round(tramo, 2),
                "venc_comp":         fv,
                "Documento_ref":     str(row.get("Documento", "")),
                "dias_vencido_item": dias,
            })

    if not filas:
        return pd.DataFrame()
    return pd.DataFrame(filas)


def correr_etl_cc(sync_drive: bool | None = None):
    print("Procesando cuentas corrientes...")
    
    # Sincronizar archivos desde Google Drive
    if _drive_sync_habilitado(sync_drive):
        try:
            _sincronizar_si_corresponde(sync_drive)
        except Exception as e:
            print(f"  ⚠ Sincronización con Drive fallida (continuando con archivos locales): {e}")
    
    try:
        movimientos, saldos = procesar_cc()
        guardar(movimientos, "cc_movimientos")
        guardar(saldos, "cc_saldos")
        print(f"  → {len(saldos)} clientes con saldo pendiente")
        print(f"  → Deuda total: ${saldos['saldo_actual'].sum():,.0f}")
        return movimientos, saldos
    except FileNotFoundError as e:
        print(f"  ✗ {e}")
        # Intentar procesar composición de saldos de forma independiente
        try:
            hoy = pd.Timestamp(date.today())
            comp = cargar_composicion_saldos(hoy)
            if comp is not None:
                print(f"  ✓ Composición procesada independientemente ({len(comp)} clientes)")
        except Exception as e_comp:
            print(f"  ⚠ Composición independiente también falló: {e_comp}")
        return None, None
    except Exception as e:
        print(f"  ✗ Error ETL cuentas corrientes: {e}")
        return None, None


if __name__ == "__main__":
    correr_etl_cc()
