"""
ETL auxiliar — Composicion de saldos
Separa la lectura/normalizacion de composicion para reutilizarla desde CC.
"""

from pathlib import Path
import re
import unicodedata
import warnings

import pandas as pd

from etl.db import guardar as db_guardar

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
    category=UserWarning,
)

RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")


def _normalizar_texto(texto: str) -> str:
    if texto is None:
        return ""
    base = unicodedata.normalize("NFKD", str(texto))
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^a-zA-Z0-9]+", "_", base).strip("_")
    return base.lower()


def normalizar_nombre_cliente(nombre: str) -> str:
    """Normaliza nombres de clientes para comparación robusta:
    sin acentos, sin puntuación, mayúsculas, espacios colapsados.
    Ej: 'PAYWAY S.A.U.' y 'Payway SAU' → 'PAYWAY SAU'
    """
    if not nombre or str(nombre).strip().lower() in ("nan", "none", ""):
        return ""
    base = unicodedata.normalize("NFKD", str(nombre))
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^A-Za-z0-9 ]+", " ", base)
    return " ".join(base.upper().split())


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
    """Detecta columnas clave probando varias filas de encabezado.
    Lee el Excel una sola vez sin encabezado y busca la fila de headers,
    evitando lecturas redundantes.
    """
    try:
        raw = pd.read_excel(path, sheet_name=hoja, header=None)
    except Exception:
        return None, None, None, None, None, None, None

    if raw is None or raw.empty:
        return None, None, None, None, None, None, None

    for header_row in range(min(8, len(raw))):
        headers = raw.iloc[header_row].astype(str).tolist()
        cols_norm = {_normalizar_texto(c): c for c in headers}

        col_cliente = _resolver_columna(cols_norm, ["cliente", "razon_social", "razonsocial"])
        col_centro  = _resolver_columna(cols_norm, ["centro_de_costo", "centro_costo", "centro", "linea_negocio", "nivel_1_dimension", "dim_valor"])
        col_saldo   = _resolver_columna(cols_norm, ["saldo_abierto", "saldo", "importe_pendiente", "pendiente", "deuda", "importe"])
        col_venc    = _resolver_columna(cols_norm, ["fecha_vencimiento", "vencimiento", "fecha_vto", "fecha_de_vencimiento"])
        col_doc     = _resolver_columna(cols_norm, ["documento", "comprobante", "factura", "numero_comprobante", "numero_factura"])

        if col_cliente and col_saldo:
            # Reconstruir DataFrame con esa fila como encabezado
            base = raw.iloc[header_row + 1:].copy()
            base.columns = headers
            base = base.reset_index(drop=True)
            # Mapear nombres normalizados a los originales del DataFrame
            col_cliente = headers[list(cols_norm.keys()).index(_normalizar_texto(col_cliente))] if col_cliente in headers else col_cliente
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

        # Forward-fill cliente: Finnegans exporta con celdas combinadas donde
        # solo la primera fila del grupo tiene el nombre y el resto es NaN.
        col_cli_serie = base[col_cliente].replace("", None).ffill()
        detalle = pd.DataFrame()
        detalle["Cliente"] = col_cli_serie.astype(str).str.strip().str.title()
        detalle["cliente_norm"] = detalle["Cliente"].map(normalizar_nombre_cliente)

        # Forward-fill centro_costo por la misma razón
        if col_centro:
            col_ctr_serie = base[col_centro].replace("", None).ffill()
            detalle["centro_costo"] = col_ctr_serie.astype(str).str.strip()
        else:
            detalle["centro_costo"] = "Sin centro"

        detalle["saldo_abierto"] = _parsear_importe_serie(base[col_saldo])
        detalle["venc_comp"] = (
            pd.to_datetime(base[col_venc], dayfirst=True, errors="coerce") if col_venc else pd.NaT
        )
        detalle["Documento_ref"] = (
            base[col_doc].astype(str).str.strip() if col_doc else ""
        )
        # Excluir filas sin cliente válido (incluyendo "Nan" residual) y saldo cero
        detalle = detalle[
            (detalle["cliente_norm"] != "") & (detalle["saldo_abierto"] > 0)
        ].copy()
        if not detalle.empty:
            frames.append(detalle)

    if not frames:
        print("  · Composicion: no se detectaron filas validas (>0) en ninguna hoja")
        return None

    comp = pd.concat(frames, ignore_index=True)
    print(f"  · Composicion: {len(comp)} filas validas detectadas")
    comp["dias_vencido_item"] = (hoy - comp["venc_comp"]).dt.days
    comp["esta_vencido"] = comp["dias_vencido_item"].fillna(0) > 0

    # Calcular saldo vencido por cliente sin lambda que capture el DataFrame externo
    comp_vencido = comp[comp["esta_vencido"]].groupby("Cliente")["saldo_abierto"].sum().rename("saldo_vencido_comp")
    resumen = comp.groupby("Cliente", as_index=False).agg(
        saldo_composicion=("saldo_abierto", "sum"),
    )
    resumen = resumen.merge(comp_vencido, on="Cliente", how="left")
    resumen["saldo_vencido_comp"] = resumen["saldo_vencido_comp"].fillna(0)
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

    db_guardar(comp, "cc_composicion")

    return resumen
