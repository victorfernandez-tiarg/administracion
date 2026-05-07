"""
ETL auxiliar — Composicion de saldos
Separa la lectura/normalizacion de composicion para reutilizarla desde CC.
"""

from pathlib import Path
import re
import unicodedata

import pandas as pd

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


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


def _parsear_importe_serie(serie: pd.Series) -> pd.Series:
    """Convierte importes con formatos locales (ej: $ 1.234,56) a float."""
    txt = serie.astype(str).str.strip()
    txt = txt.replace({"": "0", "nan": "0", "None": "0"})
    txt = txt.str.replace(r"[^0-9,\.-]", "", regex=True)

    tiene_coma = txt.str.contains(",", regex=False)
    tiene_punto = txt.str.contains(".", regex=False)

    ambos = tiene_coma & tiene_punto
    solo_coma = tiene_coma & ~tiene_punto

    txt.loc[ambos] = txt.loc[ambos].str.replace(".", "", regex=False).str.replace(",", ".", regex=False)
    txt.loc[solo_coma] = txt.loc[solo_coma].str.replace(",", ".", regex=False)

    return pd.to_numeric(txt, errors="coerce").fillna(0)


def _extraer_columnas_composicion(path: Path, hoja: str):
    """Intenta detectar columnas clave probando varias filas de encabezado."""
    for header_row in range(0, 8):
        try:
            base = pd.read_excel(path, sheet_name=hoja, header=header_row)
        except Exception:
            continue

        if base is None or base.empty:
            continue

        cols_norm = {_normalizar_texto(c): c for c in base.columns}
        col_cliente = _resolver_columna(cols_norm, ["cliente", "razon_social", "razonsocial"])
        col_centro = _resolver_columna(cols_norm, ["centro_de_costo", "centro_costo", "centro", "linea_negocio", "nivel_1_dimension", "dim_valor"])
        col_saldo = _resolver_columna(cols_norm, ["saldo_abierto", "saldo", "importe_pendiente", "pendiente", "deuda", "importe"])
        col_venc = _resolver_columna(cols_norm, ["fecha_vencimiento", "vencimiento", "fecha_vto", "fecha_de_vencimiento"])
        col_doc = _resolver_columna(cols_norm, ["documento", "comprobante", "factura", "numero_comprobante", "numero_factura"])

        if col_cliente and col_saldo:
            return base, col_cliente, col_centro, col_saldo, col_venc, col_doc, header_row

    return None, None, None, None, None, None, None


def buscar_archivo_composicion() -> Path | None:
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
    path = buscar_archivo_composicion()
    if not path:
        print("  · Composicion: no se encontro archivo en data/raw")
        return None

    print(f"  · Composicion: intentando cargar {path.name}")

    try:
        xls = pd.ExcelFile(path)
    except Exception:
        return None

    frames = []
    for hoja in xls.sheet_names:
        base, col_cliente, col_centro, col_saldo, col_venc, col_doc, header_row = _extraer_columnas_composicion(path, hoja)

        if base is None or base.empty:
            continue

        if not col_cliente or not col_saldo:
            continue

        print(
            f"    - Hoja '{hoja}': header fila {header_row + 1}, "
            f"cliente='{col_cliente}', saldo='{col_saldo}'"
        )

        detalle = pd.DataFrame()
        detalle["Cliente"] = base[col_cliente].astype(str).str.strip().str.title()
        detalle["centro_costo"] = (
            base[col_centro].astype(str).str.strip() if col_centro else "Sin centro"
        )
        detalle["saldo_abierto"] = _parsear_importe_serie(base[col_saldo])
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
        print("  · Composicion: no se detectaron filas validas (>0) en ninguna hoja")
        return None

    comp = pd.concat(frames, ignore_index=True)
    print(f"  · Composicion: {len(comp)} filas validas detectadas")
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
