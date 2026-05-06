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
import json
import re
import unicodedata

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


def _normalizar_texto(texto: str) -> str:
    if texto is None:
        return ""
    base = unicodedata.normalize("NFKD", str(texto))
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_")
    return base.lower()


def _resolver_columna(cols_norm: dict, candidatos: list[str]) -> str | None:
    for candidato in candidatos:
        if candidato in cols_norm:
            return cols_norm[candidato]
    for norm, original in cols_norm.items():
        if any(candidato in norm for candidato in candidatos):
            return original
    return None


def _buscar_archivo_composicion() -> Path | None:
    candidatos_directos = [
        RAW_DIR / "composicion_saldos.xlsx",
        RAW_DIR / "composicion_de_saldos.xlsx",
        RAW_DIR / "cc_composicion.xlsx",
    ]
    for path in candidatos_directos:
        if path.exists():
            return path

    patrones = ["*composicion*.xlsx", "*composición*.xlsx", "Reporte*.xlsx", "*saldos*.xlsx"]
    for patron in patrones:
        for path in sorted(RAW_DIR.glob(patron)):
            if path.name.lower() == "cc_clientes.xlsx":
                continue
            return path
    return None


def cargar_composicion_saldos(hoy: pd.Timestamp) -> pd.DataFrame | None:
    path = _buscar_archivo_composicion()
    if not path:
        return None

    try:
        xls = pd.ExcelFile(path)
    except Exception:
        return None

    frames = []
    for hoja in xls.sheet_names:
        try:
            base = pd.read_excel(path, sheet_name=hoja)
        except Exception:
            continue
        if base.empty:
            continue

        cols_norm = {_normalizar_texto(c): c for c in base.columns}
        col_cliente = _resolver_columna(cols_norm, ["cliente", "razon_social", "razonsocial"]) 
        col_centro = _resolver_columna(cols_norm, ["centro_de_costo", "centro_costo", "centro", "linea_negocio", "nivel_1_dimension", "dim_valor"])
        col_saldo = _resolver_columna(cols_norm, ["saldo_abierto", "saldo", "importe_pendiente", "pendiente", "deuda"])
        col_venc = _resolver_columna(cols_norm, ["fecha_vencimiento", "vencimiento", "fecha_vto", "fecha_de_vencimiento"])
        col_doc = _resolver_columna(cols_norm, ["documento", "comprobante", "factura", "numero_comprobante", "numero_factura"])

        if not col_cliente or not col_saldo:
            continue

        detalle = pd.DataFrame()
        detalle["Cliente"] = base[col_cliente].astype(str).str.strip().str.title()
        detalle["centro_costo"] = (
            base[col_centro].astype(str).str.strip() if col_centro else "Sin centro"
        )
        detalle["saldo_abierto"] = pd.to_numeric(base[col_saldo], errors="coerce").fillna(0)
        detalle["venc_comp"] = (
            pd.to_datetime(base[col_venc], dayfirst=True, errors="coerce") if col_venc else pd.NaT
        )
        detalle["Documento_ref"] = (
            base[col_doc].astype(str).str.strip() if col_doc else ""
        )
        detalle = detalle[(detalle["Cliente"] != "") & (detalle["saldo_abierto"] > 0)].copy()
        if not detalle.empty:
            frames.append(detalle)

    if not frames:
        return None

    comp = pd.concat(frames, ignore_index=True)
    comp["dias_vencido_item"] = (hoy - comp["venc_comp"]).dt.days
    comp["esta_vencido"] = comp["dias_vencido_item"].fillna(0) > 0

    resumen = (
        comp.groupby("Cliente", as_index=False)
        .agg(
            saldo_composicion=("saldo_abierto", "sum"),
            saldo_vencido_comp=("saldo_abierto", lambda s: s[comp.loc[s.index, "esta_vencido"]].sum()),
        )
    )
    resumen["saldo_por_vencer_comp"] = (resumen["saldo_composicion"] - resumen["saldo_vencido_comp"]).clip(lower=0)

    vencidos = comp[comp["esta_vencido"]].copy()
    if not vencidos.empty:
        dias_pond = (
            vencidos.groupby("Cliente")
            .apply(
                lambda g: int(round((g["saldo_abierto"] * g["dias_vencido_item"]).sum() / g["saldo_abierto"].sum(), 0))
                if g["saldo_abierto"].sum() > 0
                else 0
            )
            .rename("dias_vencido_comp")
            .reset_index()
        )
        dias_max = (
            vencidos.groupby("Cliente", as_index=False)["dias_vencido_item"]
            .max()
            .rename(columns={"dias_vencido_item": "dias_vencido_max_comp"})
        )
        venc_min = (
            vencidos.groupby("Cliente", as_index=False)["venc_comp"]
            .min()
            .rename(columns={"venc_comp": "venc_comp_min"})
        )
        resumen = resumen.merge(dias_pond, on="Cliente", how="left")
        resumen = resumen.merge(dias_max, on="Cliente", how="left")
        resumen = resumen.merge(venc_min, on="Cliente", how="left")
    else:
        resumen["dias_vencido_comp"] = 0
        resumen["dias_vencido_max_comp"] = 0
        resumen["venc_comp_min"] = pd.NaT

    centros = (
        comp.groupby(["Cliente", "centro_costo"], as_index=False)["saldo_abierto"]
        .sum()
        .sort_values(["Cliente", "saldo_abierto"], ascending=[True, False])
    )
    centro_principal = (
        centros.groupby("Cliente", as_index=False)
        .first()[["Cliente", "centro_costo"]]
        .rename(columns={"centro_costo": "centro_costo_principal"})
    )
    centros_lista = (
        centros.groupby("Cliente", as_index=False)["centro_costo"]
        .agg(lambda vals: " | ".join(dict.fromkeys([v for v in vals if str(v).strip()])))
        .rename(columns={"centro_costo": "centros_costo"})
    )

    resumen = resumen.merge(centro_principal, on="Cliente", how="left")
    resumen = resumen.merge(centros_lista, on="Cliente", how="left")
    resumen["fuente_aging"] = "composicion"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    try:
        comp.to_parquet(PROCESSED_DIR / "cc_composicion.parquet", index=False)
    except ImportError:
        comp.to_csv(PROCESSED_DIR / "cc_composicion.csv", index=False)

    return resumen


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
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    df["Cliente"]    = df["Cliente"].str.strip().str.title()
    df["Documento"]  = df["Documento"].fillna("").str.strip()
    df["Descripción"] = df["Descripción"].fillna("")
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


def guardar_csv(df: pd.DataFrame, nombre: str):
    """Guarda como parquet si pyarrow disponible, sino CSV."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(PROCESSED_DIR / f"{nombre}.parquet", index=False)
        print(f"  ✓ {nombre}.parquet ({len(df)} filas)")
    except ImportError:
        df.to_csv(PROCESSED_DIR / f"{nombre}.csv", index=False)
        print(f"  ✓ {nombre}.csv ({len(df)} filas)")


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
