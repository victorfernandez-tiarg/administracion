
"""
Finnegans BI — Dashboard Híbrido
Facturación + Cuentas Corrientes reales de Finnegans GO
"""
 
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path
import os
import io
import json, sys
from datetime import date
 
#streamlit run dashboard/app.py 
sys.path.append(str(Path(__file__).parent.parent))
from etl.procesar    import correr_etl
from etl.procesar_cc import correr_etl_cc
from etl.sync_drive  import sincronizar
from dashboard.asistente import (
    generar_contexto, consultar_ollama,
    ollama_disponible, modelos_disponibles,
)
 
 
 
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
ASSETS_DIR = Path(__file__).parent / "assets"
 
st.set_page_config(page_title="Finnegans BI", page_icon="📊", layout="wide")
 
# ── Paleta ─────────────────────────────────────────
C_LOCAL  = "#0ea5e9"
C_INT    = "#f59e0b"
C_TOTAL  = "#6366f1"
C_ROJO   = "#ef4444"
C_VERDE  = "#22c55e"
C_TINTA  = "#0f172a"
C_MUTED  = "#64748b"
C_LINEA  = "#dbe4f0"
C_PANEL  = "#f8fafc"
 
AGING_COLOR = {
    "Al día":      C_VERDE,
    "1–30 días":   "#84cc16",
    "31–60 días":  "#f59e0b",
    "61–90 días":  "#f97316",
    "+90 días":    C_ROJO,
}
AGING_ORDEN = ["Al día", "1–30 días", "31–60 días", "61–90 días", "+90 días"]
 
COLORES_LINEA = {
    "ACRONIS":         "#0B132B",
    "SW FACTORY":      "#E11D48",
    "SF TERCERIZADO":  "#16A34A",
    "SOPORTE":         "#D97706",
    "OTROS SERVICIOS": "#0891B2",
    "STAFFING":        "#7C3AED",
    "ESPECIALES":      "#DC2626",
    "CODEWAVE":        "#2563EB",
    "ESTRUCTURA":      "#4B5563",
    "RESTO":           "#111827",
    "OTROS":           "#475569",
    "SIN LINEA":       "#6B7280",
    "SIN LÍNEA":       "#6B7280",
}
 
NOTAS_CREDITO = [
    "Nota de Crédito de Ventas Electrónica",
    "FCE Nota de Crédito de Ventas Electrónica MIPymes",
]

THEME_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');

    :root {{
        --bg-top: #f8fbff;
        --bg-bottom: #eef4fb;
        --panel: rgba(255,255,255,0.88);
        --panel-solid: #ffffff;
        --border: {C_LINEA};
        --text: {C_TINTA};
        --muted: {C_MUTED};
        --accent: {C_LOCAL};
        --accent-soft: rgba(14, 165, 233, 0.10);
        --secondary-soft: rgba(245, 158, 11, 0.10);
        --shadow: 0 18px 50px rgba(15, 23, 42, 0.06);
        --shadow-soft: 0 8px 22px rgba(15, 23, 42, 0.05);
        --sidebar-bg-top: #0f172a;
        --sidebar-bg-bottom: #111827;
        --sidebar-text: #e5eef8;
        --sidebar-muted: #94a3b8;
        --radius-lg: 22px;
        --radius-md: 16px;
    }}

    .stApp {{
        background:
            radial-gradient(circle at top left, rgba(14,165,233,0.12), transparent 28%),
            radial-gradient(circle at top right, rgba(245,158,11,0.10), transparent 24%),
            linear-gradient(180deg, var(--bg-top) 0%, var(--bg-bottom) 100%);
        color: var(--text);
        font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
    }}

    [data-testid="stHeader"] {{
        background: rgba(248, 250, 252, 0.72);
        backdrop-filter: blur(10px);
    }}

    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, var(--sidebar-bg-top) 0%, var(--sidebar-bg-bottom) 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.06);
    }}

    [data-testid="stSidebar"] * {{
        color: var(--sidebar-text);
    }}

    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] .stMarkdown {{
        color: var(--sidebar-muted) !important;
    }}

    [data-testid="stSidebar"] [data-testid="stImage"] img {{
        margin: 0 auto 0.55rem auto;
        display: block;
        filter: drop-shadow(0 12px 28px rgba(0, 0, 0, 0.22));
    }}

    [data-testid="stSidebar"] hr {{
        background: linear-gradient(90deg, rgba(255,255,255,0), rgba(148,163,184,0.30), rgba(255,255,255,0));
    }}

    [data-testid="stSidebar"] div[data-baseweb="select"],
    [data-testid="stSidebar"] div[data-baseweb="input"],
    [data-testid="stSidebar"] [data-testid="stDateInput"] > div,
    [data-testid="stSidebar"] [data-testid="stRadio"] {{
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: none;
    }}

    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stDownloadButton > button {{
        background: rgba(255,255,255,0.06);
        color: var(--sidebar-text);
        border: 1px solid rgba(255,255,255,0.10);
    }}

    [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background: linear-gradient(90deg, rgba(14,165,233,0.24) 0%, rgba(56,189,248,0.18) 100%);
        border-color: rgba(56,189,248,0.24);
    }}

    .block-container {{
        padding-top: 5.6rem;
        padding-bottom: 2.2rem;
    }}

    h1, h2, h3, h4 {{
        color: var(--text);
        letter-spacing: -0.02em;
        font-family: 'Manrope', 'Segoe UI', Arial, sans-serif;
        font-weight: 800;
    }}

    p, label, .stCaption, .stMarkdown, .stText {{
        color: var(--text);
    }}

    [data-testid="stMetric"] {{
        background: linear-gradient(180deg, rgba(255,255,255,0.94) 0%, rgba(248,250,252,0.96) 100%);
        border: 1px solid rgba(219, 228, 240, 0.95);
        border-radius: var(--radius-md);
        padding: 1rem 1.1rem;
        box-shadow: var(--shadow-soft);
    }}

    [data-testid="stMetricLabel"] {{
        color: var(--muted);
        font-weight: 600;
        letter-spacing: 0.01em;
    }}

    [data-testid="stMetricValue"] {{
        color: var(--text);
        letter-spacing: -0.03em;
        font-family: 'Manrope', 'Segoe UI', Arial, sans-serif;
    }}

    [data-testid="stMetricDelta"] {{
        font-weight: 600;
    }}

    [data-testid="stExpander"],
    div[data-baseweb="select"],
    div[data-baseweb="input"],
    [data-testid="stDateInput"] > div,
    [data-testid="stRadio"] {{
        background: rgba(255,255,255,0.62);
        border: 1px solid rgba(219, 228, 240, 0.95);
        border-radius: var(--radius-md);
        box-shadow: none;
    }}

    [data-testid="stDataFrame"],
    [data-testid="stPlotlyChart"] {{
        background: transparent;
        border: none;
        box-shadow: none;
        padding: 0.15rem 0;
    }}

    [data-testid="stExpander"] {{
        overflow: hidden;
        box-shadow: var(--shadow-soft);
    }}

    [data-testid="stExpander"] details summary {{
        background: linear-gradient(90deg, rgba(15,23,42,0.035) 0%, rgba(255,255,255,0) 70%);
        border-radius: 14px;
        padding: 0.35rem 0.45rem;
    }}

    [data-testid="stChatInput"] {{
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(219,228,240,0.95);
        border-radius: 16px;
        box-shadow: none;
    }}

    .stButton > button,
    .stDownloadButton > button {{
        border-radius: 999px;
        border: 1px solid rgba(219, 228, 240, 0.95);
        font-weight: 600;
        transition: all 0.18s ease;
        box-shadow: none;
    }}

    .stButton > button:hover,
    .stDownloadButton > button:hover {{
        transform: translateY(-1px);
        box-shadow: var(--shadow-soft);
    }}

    div[data-testid="stTabs"] {{
        position: relative;
        z-index: 10;
    }}

    div[data-testid="stTabs"] > div {{
        overflow: visible !important;
    }}

    div[data-testid="stTabs"]:first-of-type {{
        position: fixed;
        top: 0.35rem;
        left: 50%;
        transform: translateX(-50%);
        width: min(1120px, calc(100vw - 4rem));
        z-index: 999;
    }}

    .stTabs [data-baseweb="tab-list"],
    .stTabs [role="tablist"] {{
        gap: 0.35rem;
        background: rgba(255,255,255,0.55);
        padding: 0.35rem;
        border-radius: 999px;
        border: 1px solid rgba(219, 228, 240, 0.9);
        position: relative;
        z-index: 81;
        backdrop-filter: blur(8px);
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 999px;
        color: var(--muted);
        font-weight: 600;
        padding: 0.45rem 0.95rem;
        font-family: 'Manrope', 'Segoe UI', Arial, sans-serif;
        border: 1px solid transparent;
    }}

    .stTabs [aria-selected="true"] {{
        background: rgba(255,255,255,0.92);
        color: var(--text) !important;
        border-color: rgba(148,163,184,0.24);
        box-shadow: var(--shadow-soft);
    }}

    [data-baseweb="radio"] > div[aria-checked="true"] {{
        background: rgba(255,255,255,0.92) !important;
        border-color: rgba(148,163,184,0.24) !important;
        box-shadow: var(--shadow-soft) !important;
        color: var(--text) !important;
    }}

    [data-baseweb="radio"] > div[aria-checked="true"] * {{
        color: var(--text) !important;
    }}

    hr {{
        border: none;
        height: 1px;
        background: linear-gradient(90deg, rgba(148,163,184,0), rgba(148,163,184,0.45), rgba(148,163,184,0));
        margin: 1.1rem 0 1.35rem 0;
    }}
</style>
"""

pio.templates["finnegans_min"] = go.layout.Template(
    layout=go.Layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0)",
        font=dict(color=C_TINTA, family="Inter, Segoe UI, Arial, sans-serif"),
        title=dict(font=dict(color=C_TINTA, size=18)),
        colorway=["#0f172a", "#1d4ed8", "#2563eb", "#1e40af", "#0369a1", "#334155", "#94a3b8"],
        legend=dict(bgcolor="rgba(255,255,255,0.82)", bordercolor="rgba(219,228,240,0.9)", borderwidth=1),
        xaxis=dict(
            showgrid=True,
            gridcolor="rgba(148,163,184,0.16)",
            zeroline=False,
            linecolor="rgba(148,163,184,0.28)",
            tickfont=dict(color=C_MUTED),
            title_font=dict(color=C_MUTED),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(148,163,184,0.16)",
            zeroline=False,
            linecolor="rgba(148,163,184,0.28)",
            tickfont=dict(color=C_MUTED),
            title_font=dict(color=C_MUTED),
        ),
        margin=dict(t=30, b=20, l=20, r=20),
    )
)
pio.templates.default = "finnegans_min"
st.markdown(THEME_CSS, unsafe_allow_html=True)
 
# ── Helpers ────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load(nombre):
    for ext in ("parquet", "csv"):
        p = PROCESSED_DIR / f"{nombre}.{ext}"
        if p.exists():
            return pd.read_parquet(p) if ext == "parquet" else pd.read_csv(p, parse_dates=True)
    return None
 
def fmt_m(v, moneda="ARS"):
    if moneda == "USD":
        if abs(v) >= 1_000_000_000: return f"USD {v/1_000_000_000:.2f}B"
        if abs(v) >= 1_000_000:     return f"USD {v/1_000_000:.2f}M"
        if abs(v) >= 1_000:         return f"USD {v/1_000:.1f}K"
        return f"USD {v:,.0f}"
    if abs(v) >= 1_000_000: return f"$ {v/1_000_000:.1f}M"
    if abs(v) >= 1_000:     return f"$ {v/1_000:.0f}K"
    return f"$ {v:.0f}"
 
@st.cache_data(show_spinner=False)
def load_meta():
    p = PROCESSED_DIR / "meta.json"
    return json.load(open(p)) if p.exists() else {}


def _normalizar_columna(nombre: str) -> str:
    return "".join(ch.lower() for ch in str(nombre).strip() if ch.isalnum())


def _validar_excel_bytes(archivo_bytes: bytes, columnas_requeridas: list[str]) -> tuple[bool, str]:
    try:
        xls = pd.ExcelFile(io.BytesIO(archivo_bytes))
        sheet = xls.sheet_names[0]
        df_cols = pd.read_excel(io.BytesIO(archivo_bytes), sheet_name=sheet, nrows=0)
        cols_archivo = set(df_cols.columns.astype(str).tolist())
    except Exception as e:
        return False, f"No se pudo leer Excel: {e}"

    faltantes = [col for col in columnas_requeridas if col not in cols_archivo]
    if faltantes:
        return False, "Faltan columnas requeridas: " + ", ".join(faltantes)
    return True, "OK"


def _validar_composicion_bytes(archivo_bytes: bytes) -> tuple[bool, str]:
    candidatos_cliente = {"cliente", "razonsocial", "razon_social"}
    candidatos_saldo = {"saldoabierto", "saldo", "importependiente", "pendiente", "deuda"}

    try:
        xls = pd.ExcelFile(io.BytesIO(archivo_bytes))
    except Exception as e:
        return False, f"No se pudo leer Excel: {e}"

    for sheet in xls.sheet_names:
        try:
            df_cols = pd.read_excel(io.BytesIO(archivo_bytes), sheet_name=sheet, nrows=0)
        except Exception:
            continue
        cols_norm = {_normalizar_columna(c) for c in df_cols.columns.astype(str).tolist()}
        tiene_cliente = any(c in cols_norm for c in candidatos_cliente)
        tiene_saldo = any(c in cols_norm for c in candidatos_saldo)
        if tiene_cliente and tiene_saldo:
            return True, "OK"

    return False, "No se detectaron columnas de cliente y saldo en ninguna hoja"


def _guardar_adjunto_en_raw(uploaded_file, destino: Path) -> int:
    contenido = uploaded_file.getvalue()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return len(contenido)


def calcular_kpis_financieros(df_fact: pd.DataFrame, df_cc: pd.DataFrame) -> dict:
    kpis = {
        "dso": 0.0,
        "overdue_ratio": 0.0,
        "top5_concentracion": 0.0,
        "cobertura_30d": 0.0,
        "facturacion_90d": 0.0,
    }
    if df_cc is None or df_cc.empty:
        return kpis

    saldo_comp = (
        pd.to_numeric(df_cc.get("saldo_composicion", 0), errors="coerce").fillna(0)
        if "saldo_composicion" in df_cc.columns
        else pd.Series(0, index=df_cc.index)
    )
    saldo_actual = pd.to_numeric(df_cc.get("saldo_actual", 0), errors="coerce").fillna(0)
    saldo_deuda = saldo_comp.where(saldo_comp > 0, saldo_actual)

    deuda_total = saldo_deuda.sum()
    saldo_vencido = pd.to_numeric(df_cc.get("saldo_vencido", 0), errors="coerce").fillna(0).sum()
    kpis["overdue_ratio"] = (saldo_vencido / deuda_total * 100) if deuda_total > 0 else 0

    top5 = (
        saldo_deuda
        .nlargest(5)
        .sum()
    )
    kpis["top5_concentracion"] = (top5 / deuda_total * 100) if deuda_total > 0 else 0

    if "dias_vencido" in df_cc.columns and "saldo_vencido" in df_cc.columns:
        venc_30 = df_cc[pd.to_numeric(df_cc["dias_vencido"], errors="coerce").fillna(0) <= 30]
        saldo_venc_30 = pd.to_numeric(venc_30["saldo_vencido"], errors="coerce").fillna(0).sum()
        kpis["cobertura_30d"] = (saldo_venc_30 / saldo_vencido * 100) if saldo_vencido > 0 else 0

    if df_fact is not None and not df_fact.empty and "fecha" in df_fact.columns and "monto_total_ars" in df_fact.columns:
        base = df_fact.copy()
        base["fecha"] = pd.to_datetime(base["fecha"], errors="coerce")
        fecha_max = base["fecha"].max()
        if pd.notna(fecha_max):
            desde = fecha_max - pd.Timedelta(days=89)
            ult_90 = base[base["fecha"] >= desde]
            fact_90 = pd.to_numeric(ult_90["monto_total_ars"], errors="coerce").fillna(0).sum()
            kpis["facturacion_90d"] = fact_90
            venta_diaria = fact_90 / 90 if fact_90 > 0 else 0
            kpis["dso"] = (deuda_total / venta_diaria) if venta_diaria > 0 else 0

    return kpis


def _ultima_modificacion(paths):
    existentes = [path.stat().st_mtime for path in paths if path.exists()]
    return max(existentes) if existentes else None


def _dataset_desactualizado(raw_paths, processed_paths):
    mod_raw = _ultima_modificacion(raw_paths)
    if mod_raw is None:
        return False
    mod_processed = _ultima_modificacion(processed_paths)
    if mod_processed is None:
        return True
    return mod_raw > mod_processed


def auto_actualizar_desde_archivos_locales():
    tareas = []

    raw_cc_candidates = [
        RAW_DIR / "cc_clientes.xlsx",
        RAW_DIR / "composicion_saldos.xlsx",
        RAW_DIR / "composicion_de_saldos.xlsx",
        RAW_DIR / "cc_composicion.xlsx",
    ]
    raw_cc_candidates.extend(sorted(RAW_DIR.glob("Reporte*.xlsx")))

    if _dataset_desactualizado(
        [RAW_DIR / "datos_facturacion.xlsx"],
        [
            PROCESSED_DIR / "facturas.parquet",
            PROCESSED_DIR / "facturas.csv",
            PROCESSED_DIR / "resumen_clientes.parquet",
            PROCESSED_DIR / "resumen_clientes.csv",
            PROCESSED_DIR / "meta.json",
        ],
    ):
        tareas.append(("facturación", lambda: correr_etl(sync_drive=False)))

    if _dataset_desactualizado(
        raw_cc_candidates,
        [
            PROCESSED_DIR / "cc_movimientos.parquet",
            PROCESSED_DIR / "cc_movimientos.csv",
            PROCESSED_DIR / "cc_saldos.parquet",
            PROCESSED_DIR / "cc_saldos.csv",
            PROCESSED_DIR / "cc_composicion.parquet",
            PROCESSED_DIR / "cc_composicion.csv",
        ],
    ):
        tareas.append(("cuentas corrientes", lambda: correr_etl_cc(sync_drive=False)))

    if not tareas:
        return []

    actualizados = []
    with st.spinner("Detecté cambios en data/raw y estoy reprocesando automáticamente..."):
        for nombre, ejecutar in tareas:
            resultado = ejecutar()
            if isinstance(resultado, tuple):
                exito = all(valor is not None for valor in resultado)
            else:
                exito = resultado is not None
            if exito:
                actualizados.append(nombre)
    return actualizados


datasets_actualizados = auto_actualizar_desde_archivos_locales()
if datasets_actualizados:
    st.cache_data.clear()
auto_sync_drive = os.getenv("AUTO_SYNC_DRIVE", "true").strip().lower() in {"1", "true", "yes", "si"}
 
# ── Cargar datos (antes del sidebar para calcular rango) ──
df_fact_raw = load("facturas")
df_saldos   = load("cc_saldos")
df_cc_mov   = load("cc_movimientos")
df_cc_comp  = load("cc_composicion")
 
sin_fact = df_fact_raw is None
sin_cc   = df_saldos is None
sin_comp = df_cc_comp is None
 
# Calcular rango de fechas disponible en los datos
fecha_min_default = date(2024, 1, 1)
fecha_max_default = date.today()
if not sin_fact and "fecha" in df_fact_raw.columns:
    fechas_validas = pd.to_datetime(df_fact_raw["fecha"], errors="coerce").dropna()
    if not fechas_validas.empty:
        fecha_min_default = fechas_validas.min().date()
        fecha_max_default = fechas_validas.max().date()

fact_rows = 0 if sin_fact else len(df_fact_raw)
cc_rows = 0 if sin_cc else len(df_saldos)
comp_rows = 0 if sin_comp else len(df_cc_comp)

clientes_opts = []
if not sin_fact and "cliente" in df_fact_raw.columns:
    clientes_opts.extend(df_fact_raw["cliente"].dropna().astype(str).str.strip().str.title().tolist())
if not sin_cc and "Cliente" in df_saldos.columns:
    clientes_opts.extend(df_saldos["Cliente"].dropna().astype(str).str.strip().str.title().tolist())
clientes_opts = sorted(set([c for c in clientes_opts if c]))

centros_opts = []
if not sin_fact and "linea_negocio" in df_fact_raw.columns:
    centros_opts.extend(df_fact_raw["linea_negocio"].dropna().astype(str).str.strip().tolist())
if not sin_comp and "centro_costo" in df_cc_comp.columns:
    centros_opts.extend(df_cc_comp["centro_costo"].dropna().astype(str).str.strip().tolist())
if not sin_cc and "centro_costo_principal" in df_saldos.columns:
    centros_opts.extend(df_saldos["centro_costo_principal"].dropna().astype(str).str.strip().tolist())
centros_opts = sorted(set([c for c in centros_opts if c]))
 
# ── Sidebar ────────────────────────────────────────
with st.sidebar:
 
    logo_path = ASSETS_DIR / "logo_empresa.png"
    if logo_path.exists():
        st.image(str(logo_path), width=220)
    else:
        st.markdown("""
            <div style="padding: 6px 0 14px 0;">
                <div style="font-size:22px; font-weight:700; letter-spacing:-0.5px; color:#6366f1;">
                    TIARG
                </div>
                <div style="font-size:10px; color:#888; letter-spacing:0.15em; text-transform:uppercase; margin-top:2px;">
                    Financial Intelligence
                </div>
            </div>
        """, unsafe_allow_html=True)
 
    st.markdown("---")

    st.markdown("**Carga de archivos**")
    if "adjuntos_status" in st.session_state:
        st.success(st.session_state.pop("adjuntos_status"))

    up_fact = st.file_uploader(
        "Facturación",
        type=["xlsx"],
        key="upload_fact",
        help="Se guarda como data/raw/datos_facturacion.xlsx",
    )
    up_cc = st.file_uploader(
        "Ctas. Ctes.",
        type=["xlsx"],
        key="upload_cc",
        help="Se guarda como data/raw/cc_clientes.xlsx",
    )
    up_comp = st.file_uploader(
        "Composición de saldos",
        type=["xlsx"],
        key="upload_comp",
        help="Se guarda como data/raw/composicion_saldos.xlsx",
    )

    if st.button("📎 Validar y procesar adjuntos", type="primary"):
        if up_fact is None and up_cc is None and up_comp is None:
            st.warning("Adjuntá al menos un archivo para procesar.")
        else:
            errores = []
            guardados = []

            if up_fact is not None:
                ok, msg = _validar_excel_bytes(
                    up_fact.getvalue(),
                    ["Fecha", "Cliente", "Empresa", "Moneda", "Documento", "Importe mon. principal", "Imp. usd", "Nivel 1 dimensión"],
                )
                if not ok:
                    errores.append(f"Facturación: {msg}")
                else:
                    _guardar_adjunto_en_raw(up_fact, RAW_DIR / "datos_facturacion.xlsx")
                    guardados.append("Facturación")

            if up_cc is not None:
                ok, msg = _validar_excel_bytes(
                    up_cc.getvalue(),
                    ["Fecha", "Fecha vencimiento", "Cliente", "Documento", "Debe ppal", "Haber ppal", "Saldo ppal"],
                )
                if not ok:
                    errores.append(f"Ctas. Ctes.: {msg}")
                else:
                    _guardar_adjunto_en_raw(up_cc, RAW_DIR / "cc_clientes.xlsx")
                    guardados.append("Ctas. Ctes.")

            if up_comp is not None:
                ok, msg = _validar_composicion_bytes(up_comp.getvalue())
                if not ok:
                    errores.append(f"Composición: {msg}")
                else:
                    _guardar_adjunto_en_raw(up_comp, RAW_DIR / "composicion_saldos.xlsx")
                    guardados.append("Composición")

            if errores:
                st.error("No se pudo procesar por validaciones:\n- " + "\n- ".join(errores))
            else:
                with st.spinner("Validado. Procesando archivos adjuntos..."):
                    facturas = correr_etl(sync_drive=False)
                    _, saldos = correr_etl_cc(sync_drive=False)

                if facturas is None or saldos is None:
                    st.error("El ETL falló luego de cargar adjuntos. Revisá formato y logs.")
                else:
                    st.cache_data.clear()
                    comp_actualizado = load("cc_composicion")
                    comp_procesadas = 0 if comp_actualizado is None else len(comp_actualizado)
                    st.session_state["adjuntos_status"] = (
                        f"Procesado desde adjuntos ({', '.join(guardados)}). "
                        f"Registros: Facturación {len(facturas):,} · CC {len(saldos):,} · Composición {comp_procesadas:,}"
                    )
                    for k in ["fecha_desde", "fecha_hasta"]:
                        st.session_state.pop(k, None)
                    st.rerun()

    st.markdown("---")

    if st.button("⬇️ Sincronizar Drive"):
        with st.spinner("Descargando desde Drive y reprocesando..."):
            try:
                resultados_sync = sincronizar()
                facturas = correr_etl(sync_drive=False)
                _, saldos = correr_etl_cc(sync_drive=False)
                if facturas is None or saldos is None:
                    raise RuntimeError("Falló el ETL luego de sincronizar Drive.")
                ok_comp = resultados_sync.get("composicion_saldos.xlsx", False) if isinstance(resultados_sync, dict) else False
                if not ok_comp:
                    st.warning(
                        "Sincronización parcial: no se pudo descargar composicion_saldos.xlsx. "
                        "Revisá GOOGLE_DRIVE_COMPOSICION_FILE_ID y permisos del archivo para el service account."
                    )
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")

    if st.button("♻️ Reprocesar todo", type="primary"):
        with st.spinner("Procesando Excel locales..."):
            facturas = correr_etl(sync_drive=False)
            _, saldos = correr_etl_cc(sync_drive=False)
        if facturas is None:
            st.error("ETL de facturación falló. Revisá el archivo local en data/raw/datos_facturacion.xlsx.")
        elif saldos is None:
            st.error("ETL de cuentas corrientes falló. Revisá el archivo local en data/raw/cc_clientes.xlsx.")
        else:
            st.cache_data.clear()
            for k in ["fecha_desde", "fecha_hasta"]:
                st.session_state.pop(k, None)
            st.rerun()
 
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Facturación", type="primary"):
            with st.spinner("Procesando..."):
                facturas = correr_etl()
            if facturas is None:
                st.error("ETL de facturación falló. Revisá el archivo local y los logs.")
            else:
                st.cache_data.clear(); st.rerun()
    with col2:
        if st.button("🔄 Ctas. Ctes.", type="primary"):
            with st.spinner("Procesando..."):
                _, saldos = correr_etl_cc()
            if saldos is None:
                st.error("ETL de cuentas corrientes falló. Revisá el archivo local y los logs.")
            else:
                st.cache_data.clear(); st.rerun()

    st.caption(
        f"Registros cargados · Facturación: {fact_rows:,} · CC: {cc_rows:,} · Composición: {comp_rows:,}"
    )
 
    st.markdown("---")
    st.markdown("**Empresa**")
    empresa = st.radio("emp", ["Todas", "Local (TIARG S.A.)", "Internacional (TIARG LLC)"],
                       label_visibility="collapsed")

    st.markdown("---")
    st.markdown("**Filtros Globales**")
    clientes_sel = st.multiselect("Clientes", clientes_opts, key="filtro_global_clientes")
    centros_sel = st.multiselect("Centros de costo", centros_opts, key="filtro_global_centros")
 
    st.markdown("---")
 
    # ── Asistente IA ────────────────────────────────
    st.markdown("**🤖 Asistente IA**")
    ia_activo = ollama_disponible()
    if not ia_activo:
        st.caption("⚠️ Ollama no disponible. Iniciá con `ollama serve`.")
    else:
        modelos = modelos_disponibles()
        if modelos:
            st.selectbox("Modelo", modelos, key="modelo_ia", label_visibility="collapsed")
        st.caption("Hacé preguntas sobre los datos en la pestaña Asistente IA.")
 
# ── Filtrar facturación ────────────────────────────
# ═══════════════════════════════════════════════════
# TABS (arriba del contenido)
# ═══════════════════════════════════════════════════
t1, t2, t3, t4, t5, t6 = st.tabs([
    "🏠 Resumen ejecutivo",
    "📄 Facturación",
    "💳 Cuentas corrientes",
    "👥 Clientes",
    "🤖 Asistente IA",
    "📋 Detalle",
])

# ── Período — prominente, arriba del dashboard ────
st.markdown("**📅 Período**")

# Inicializar session_state con valores válidos dentro del rango disponible
fecha_desde_default = max(fecha_min_default, date(fecha_max_default.year, 1, 1))
fecha_hasta_default = fecha_max_default

if "fecha_desde" not in st.session_state or not isinstance(st.session_state["fecha_desde"], date):
    st.session_state["fecha_desde"] = fecha_desde_default
else:
    # Asegurar que el valor está dentro del rango disponible
    st.session_state["fecha_desde"] = min(max(st.session_state["fecha_desde"], fecha_min_default), fecha_max_default)

if "fecha_hasta" not in st.session_state or not isinstance(st.session_state["fecha_hasta"], date):
    st.session_state["fecha_hasta"] = fecha_hasta_default
else:
    # Asegurar que el valor está dentro del rango disponible
    st.session_state["fecha_hasta"] = min(max(st.session_state["fecha_hasta"], fecha_min_default), fecha_max_default)

pc1, pc2 = st.columns(2)
with pc1:
    fecha_desde = st.date_input(
        "Desde",
        min_value=fecha_min_default,
        max_value=fecha_max_default,
        format="DD/MM/YYYY",
        key="fecha_desde",
    )
with pc2:
    fecha_hasta = st.date_input(
        "Hasta",
        min_value=fecha_min_default,
        max_value=fecha_max_default,
        format="DD/MM/YYYY",
        key="fecha_hasta",
    )
if fecha_desde > fecha_hasta:
    st.warning("⚠️ Fecha desde > hasta, se invirtieron.")
    fecha_desde, fecha_hasta = fecha_hasta, fecha_desde
 
st.markdown("---")
 
if not sin_fact:
    df = df_fact_raw.copy()
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
 
    if empresa == "Local (TIARG S.A.)":
        df = df[df["razon_social"] == "Local"]
    elif empresa == "Internacional (TIARG LLC)":
        df = df[df["razon_social"] == "Internacional"]
 
    # Filtro por rango de fechas
    df = df[
        (df["fecha"].dt.date >= fecha_desde) &
        (df["fecha"].dt.date <= fecha_hasta)
    ]
 
    # NC siempre incluidas — sin checkbox
 
    # Split por empresa usando Importe mon. principal (correcto)
    df_sa  = df[df["razon_social"] == "Local"]    # TIARG S.A. — ARS
    df_llc = df[df["razon_social"] == "Internacional"]  # TIARG LLC — USD mon. principal
 
    df_ars = df[df["moneda_iso"] == "ARS"]  # para gráficos que requieran solo ARS
    df_usd = df[df["moneda_iso"] == "USD"]  # consolidado USD via Imp. usd
    color_p = C_LOCAL if "Local" in empresa else (C_INT if "Inter" in empresa else C_TOTAL)
else:
    df = df_ars = df_usd = df_sa = df_llc = pd.DataFrame()
    color_p = C_TOTAL
 
# ── Filtrar CC por empresa si aplica ───────────────
if not sin_cc and empresa != "Todas":
    # CC no tiene campo empresa en el export, queda sin filtro de empresa
    pass

if not sin_fact and clientes_sel:
    clientes_set = set([c.strip().title() for c in clientes_sel])
    df = df[df["cliente"].astype(str).str.strip().str.title().isin(clientes_set)]
    df_sa = df_sa[df_sa["cliente"].astype(str).str.strip().str.title().isin(clientes_set)]
    df_llc = df_llc[df_llc["cliente"].astype(str).str.strip().str.title().isin(clientes_set)]
    df_ars = df_ars[df_ars["cliente"].astype(str).str.strip().str.title().isin(clientes_set)]
    df_usd = df_usd[df_usd["cliente"].astype(str).str.strip().str.title().isin(clientes_set)]

if not sin_cc and clientes_sel:
    clientes_set = set([c.strip().title() for c in clientes_sel])
    df_saldos = df_saldos[df_saldos["Cliente"].astype(str).str.strip().str.title().isin(clientes_set)]
    if df_cc_mov is not None and "Cliente" in df_cc_mov.columns:
        df_cc_mov = df_cc_mov[df_cc_mov["Cliente"].astype(str).str.strip().str.title().isin(clientes_set)]
    if not sin_comp and "Cliente" in df_cc_comp.columns:
        df_cc_comp = df_cc_comp[df_cc_comp["Cliente"].astype(str).str.strip().str.title().isin(clientes_set)]

if centros_sel:
    centros_set = set([c.strip() for c in centros_sel])
    if not sin_fact and "linea_negocio" in df.columns:
        df = df[df["linea_negocio"].astype(str).str.strip().isin(centros_set)]
        df_sa = df_sa[df_sa["linea_negocio"].astype(str).str.strip().isin(centros_set)]
        df_llc = df_llc[df_llc["linea_negocio"].astype(str).str.strip().isin(centros_set)]
        df_ars = df_ars[df_ars["linea_negocio"].astype(str).str.strip().isin(centros_set)]
        df_usd = df_usd[df_usd["linea_negocio"].astype(str).str.strip().isin(centros_set)]

    if not sin_comp and "centro_costo" in df_cc_comp.columns:
        clientes_centro = set(
            df_cc_comp[df_cc_comp["centro_costo"].astype(str).str.strip().isin(centros_set)]["Cliente"]
            .dropna().astype(str).str.strip().str.title().tolist()
        )
        if clientes_centro and not sin_cc:
            df_saldos = df_saldos[df_saldos["Cliente"].astype(str).str.strip().str.title().isin(clientes_centro)]
            if df_cc_mov is not None and "Cliente" in df_cc_mov.columns:
                df_cc_mov = df_cc_mov[df_cc_mov["Cliente"].astype(str).str.strip().str.title().isin(clientes_centro)]

if not sin_cc:
    sin_cc = df_saldos.empty
if not sin_fact:
    sin_fact = df.empty

if not sin_cc:
    saldo_comp = (
        pd.to_numeric(df_saldos.get("saldo_composicion", 0), errors="coerce").fillna(0)
        if "saldo_composicion" in df_saldos.columns
        else pd.Series(0, index=df_saldos.index)
    )
    saldo_actual = pd.to_numeric(df_saldos.get("saldo_actual", 0), errors="coerce").fillna(0)
    df_saldos["saldo_deuda"] = saldo_comp.where(saldo_comp > 0, saldo_actual)

col_deuda_cc = "saldo_deuda" if (not sin_cc and "saldo_deuda" in df_saldos.columns) else "saldo_actual"
 
# ══════════════════════════════════════════════
# TAB 1 — RESUMEN EJECUTIVO (el Steve Jobs)
# ══════════════════════════════════════════════
with t1:
    st.markdown("### Resumen ejecutivo")
 
    # ── Fila 1: KPIs principales ──────────────
    k1, k2, k3, k4 = st.columns(4)
 
    total_sa    = df_sa["monto_total_ars"].sum()  if not df_sa.empty  else 0
    total_llc   = df_llc["monto_total_ars"].sum() if not df_llc.empty else 0
    total_usd_c = df["monto_usd"].sum()           if not df.empty     else 0
    deuda_total = df_saldos[col_deuda_cc].sum()  if not sin_cc else 0
    deuda_critica = df_saldos[df_saldos["aging"] == "+90 días"]["saldo_vencido"].sum() if not sin_cc else 0
 
    k1.metric("💰 Total Facturación TIARG S.A.",   fmt_m(total_sa))
    k2.metric("💵 Total Facturación TIARG LLC",     fmt_m(total_llc, "USD"))
    k3.metric("🌐 Consolidado USD (Imp. usd)",      fmt_m(total_usd_c, "USD"))
    k4.metric("⏳ Deuda total",     fmt_m(deuda_total),
              delta=f"{deuda_critica/deuda_total*100:.0f}% crítica" if deuda_total else None,
              delta_color="inverse")
    
    st.markdown("---")
 
    # ── Fila 2: Facturación mensual SA | LLC | Consolidado USD ───
    col_a, col_b, col_c = st.columns(3)
 
    with col_a:
        st.markdown("#### TIARG S.A. — mensual ARS")
        df_sa_ars = df_sa[df_sa["moneda_iso"] == "ARS"] if not df_sa.empty else pd.DataFrame()
        if df_sa_ars.empty:
            st.info("Sin datos TIARG S.A.")
        else:
            evol = (df_sa_ars.groupby(["año","mes","mes_nombre"])["monto_total_ars"]
                    .sum().reset_index().sort_values(["año","mes"]))
            fig = px.bar(evol, x="mes_nombre", y="monto_total_ars",
                         color_discrete_sequence=[C_LOCAL],
                         labels={"mes_nombre":"","monto_total_ars":"ARS"}, text_auto=".2s")
            fig.update_layout(showlegend=False, margin=dict(t=5,b=5), height=260)
            st.plotly_chart(fig, use_container_width=True)
 
    with col_b:
        st.markdown("#### TIARG LLC — mensual USD")
        if df_llc.empty:
            st.info("Sin datos TIARG LLC.")
        else:
            evol_llc = (df_llc.groupby(["año","mes","mes_nombre"])["monto_total_ars"]
                        .sum().reset_index().sort_values(["año","mes"]))
            fig_llc = px.bar(evol_llc, x="mes_nombre", y="monto_total_ars",
                             color_discrete_sequence=[C_INT],
                             labels={"mes_nombre":"","monto_total_ars":"USD"}, text_auto=".2s")
            fig_llc.update_layout(showlegend=False, margin=dict(t=5,b=5), height=260)
            st.plotly_chart(fig_llc, use_container_width=True)
 
    with col_c:
        st.markdown("#### Consolidado USD (Imp. usd)")
        if df.empty:
            st.info("Sin datos.")
        else:
            evol_u = (df.groupby(["año","mes","mes_nombre"])["monto_usd"]
                      .sum().reset_index().sort_values(["año","mes"]))
            fig_u = px.bar(evol_u, x="mes_nombre", y="monto_usd",
                           color_discrete_sequence=[C_TOTAL],
                           labels={"mes_nombre":"","monto_usd":"USD"}, text_auto=".2s")
            fig_u.update_layout(showlegend=False, margin=dict(t=5,b=5), height=260)
            st.plotly_chart(fig_u, use_container_width=True)
 
    st.markdown("---")
 
    # ── Fila 3: Top deudores (gráfico + tabla) ──
    st.markdown("#### 🚨 Top deudores")
    if sin_cc:
        st.info("Sin datos de CC.")
    else:
        col_d_graf, col_d_tabla = st.columns(2)

        with col_d_graf:
            aging_df = (df_saldos.groupby("aging")[col_deuda_cc].sum()
                        .reindex(AGING_ORDEN).dropna().reset_index())
            fig2 = px.bar(aging_df, x=col_deuda_cc, y="aging", orientation="h",
                          color="aging", color_discrete_map=AGING_COLOR,
                          labels={col_deuda_cc:"ARS","aging":""}, text_auto=".2s")
            fig2.update_layout(showlegend=False, margin=dict(t=5,b=5), height=260)
            st.plotly_chart(fig2, use_container_width=True)

        with col_d_tabla:
            top_d = df_saldos.head(8)[["Cliente", col_deuda_cc, "saldo_vencido", "aging", "dias_vencido"]].copy()
            evento_top_d = st.dataframe(
                top_d.rename(columns={
                    col_deuda_cc: "Saldo",
                    "saldo_vencido": "Vencido",
                    "aging": "Estado",
                    "dias_vencido": "Días pond.",
                }),
                use_container_width=True,
                hide_index=True,
                on_select="rerun",
                selection_mode="single-row",
                column_config={
                    "Saldo": st.column_config.NumberColumn(format="$ %,.0f"),
                    "Vencido": st.column_config.NumberColumn(format="$ %,.0f"),
                    "Días pond.": st.column_config.NumberColumn(format="%d días"),
                },
            )

        # ── Fila 4: Desplegable con detalle pendiente del deudor seleccionado ──
        if evento_top_d.selection["rows"]:
            i_sel = evento_top_d.selection["rows"][0]
            cliente_sel = top_d.iloc[i_sel]["Cliente"]
            with st.expander(f"📌 Cuenta corriente pendiente · {cliente_sel}", expanded=True):
                resumen_cli = df_saldos[df_saldos["Cliente"] == cliente_sel]
                if not resumen_cli.empty:
                    st.dataframe(
                        resumen_cli[["Cliente", col_deuda_cc, "saldo_vencido", "saldo_por_vencer",
                                     "aging", "dias_vencido", "dias_vencido_max", "ratio_cobranza"]]
                        .rename(columns={
                            col_deuda_cc: "Saldo actual",
                            "saldo_vencido": "Saldo vencido",
                            "saldo_por_vencer": "Saldo por vencer",
                            "aging": "Estado",
                            "dias_vencido": "Días ponderados",
                            "dias_vencido_max": "Máx. días",
                            "ratio_cobranza": "% Cobrado",
                        }),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Saldo actual": st.column_config.NumberColumn(format="$ %,.0f"),
                            "Saldo vencido": st.column_config.NumberColumn(format="$ %,.0f"),
                            "Saldo por vencer": st.column_config.NumberColumn(format="$ %,.0f"),
                            "% Cobrado": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
                        },
                    )

                if df_cc_mov is not None and "Cliente" in df_cc_mov.columns:
                    mov_cli = df_cc_mov[df_cc_mov["Cliente"] == cliente_sel].copy()
                    saldo_col = "Saldo ppal" if "Saldo ppal" in mov_cli.columns else None
                    if saldo_col:
                        mov_cli[saldo_col] = pd.to_numeric(mov_cli[saldo_col], errors="coerce")
                        mov_pend = mov_cli[mov_cli[saldo_col] > 0]
                    else:
                        mov_pend = mov_cli

                    if mov_pend.empty:
                        st.info("No hay movimientos pendientes para este cliente.")
                    else:
                        cols_pend = [
                            "Fecha", "Documento", "Descripción", "Debe ppal",
                            "Haber ppal", "Saldo ppal", "Fecha vencimiento", "tipo",
                        ]
                        cols_pend = [c for c in cols_pend if c in mov_pend.columns]
                        st.dataframe(
                            mov_pend[cols_pend].sort_values("Fecha", ascending=False) if "Fecha" in mov_pend.columns else mov_pend[cols_pend],
                            use_container_width=True,
                            hide_index=True,
                            column_config={
                                "Fecha": st.column_config.DateColumn("Fecha"),
                                "Fecha vencimiento": st.column_config.DateColumn("Vencimiento"),
                                "Debe ppal": st.column_config.NumberColumn("Debe", format="$ %.0f"),
                                "Haber ppal": st.column_config.NumberColumn("Haber", format="$ %.0f"),
                                "Saldo ppal": st.column_config.NumberColumn("Pendiente", format="$ %.0f"),
                            },
                        )
        else:
            st.caption("Seleccioná un cliente en Top deudores para ver su cuenta corriente pendiente.")

    st.markdown("---")

    # ── Fila 5: Top facturadores (tabla primero) ──
    st.markdown("#### ⭐ Top facturadores")
    if df_ars.empty:
        st.info("Sin datos de facturación.")
    else:
        top_f = (df_ars.groupby("cliente")["monto_total_ars"]
                 .sum().nlargest(8).reset_index()
                 .rename(columns={"cliente": "Cliente", "monto_total_ars": "Facturado"})).copy()

        if not sin_cc:
            top_f = top_f.merge(
                df_saldos[["Cliente", col_deuda_cc]].rename(
                    columns={"Cliente": "Cliente_cc", col_deuda_cc: "Deuda"}
                ),
                left_on="Cliente", right_on="Cliente_cc", how="left"
            ).drop(columns="Cliente_cc", errors="ignore")
            top_f["Deuda"] = top_f["Deuda"].fillna(0)

        col_f_tabla, col_f_graf = st.columns(2)
        with col_f_tabla:
            cfg_top_f = {"Facturado": st.column_config.NumberColumn(format="$ %,.0f")}
            if "Deuda" in top_f.columns:
                cfg_top_f["Deuda"] = st.column_config.NumberColumn(format="$ %,.0f")
            st.dataframe(top_f, use_container_width=True, hide_index=True, column_config=cfg_top_f)

        with col_f_graf:
            fig_top_f = px.bar(
                top_f.sort_values("Facturado"),
                x="Facturado",
                y="Cliente",
                orientation="h",
                color_discrete_sequence=[C_TOTAL],
                text_auto=".2s",
                labels={"Facturado": "ARS", "Cliente": ""},
            )
            fig_top_f.update_layout(showlegend=False, margin=dict(t=5, b=5, l=10), height=320)
            st.plotly_chart(fig_top_f, use_container_width=True)
 
 
# ══════════════════════════════════════════════
# TAB 2 — FACTURACIÓN
# ══════════════════════════════════════════════
with t2:
    if sin_fact or df.empty:
        st.info("Sin datos. Colocá datos_facturacion.xlsx en data/raw/ y actualizá.")
    else:
        c1, c2, c3 = st.columns(3)
        total_sa_t2  = df_sa["monto_total_ars"].sum()  if not df_sa.empty  else 0
        total_llc_t2 = df_llc["monto_total_ars"].sum() if not df_llc.empty else 0
        total_usd_t2 = df["monto_usd"].sum() if not df.empty else 0
        c1.metric("Total Facturación TIARG S.A.", fmt_m(total_sa_t2))
        c2.metric("Total Facturación TIARG LLC",  fmt_m(total_llc_t2, "USD"))
        c3.metric("Consolidado USD (Imp. usd)", fmt_m(total_usd_t2, "USD"))
 
        st.markdown("---")
        col_a, col_b = st.columns(2)
 
        with col_a:
            st.markdown("#### TIARG S.A. — mensual ARS")
            df_sa_ars_t2 = df_sa[df_sa["moneda_iso"] == "ARS"] if not df_sa.empty else pd.DataFrame()
            if df_sa_ars_t2.empty:
                st.info("Sin datos TIARG S.A.")
            else:
                evol = (df_sa_ars_t2.groupby(["año","mes","mes_nombre"])["monto_total_ars"]
                        .sum().reset_index().sort_values(["año","mes"]))
                fig = px.bar(evol, x="mes_nombre", y="monto_total_ars",
                             color_discrete_sequence=[C_LOCAL], text_auto=".2s",
                             labels={"mes_nombre":"","monto_total_ars":"ARS"})
                fig.update_layout(showlegend=False, margin=dict(t=5,b=5))
                st.plotly_chart(fig, use_container_width=True)
 
        with col_b:
            st.markdown("#### TIARG LLC — mensual USD")
            if df_llc.empty:
                st.info("Sin facturas TIARG LLC en el período.")
            else:
                evol_llc = (df_llc.groupby(["año","mes","mes_nombre"])["monto_total_ars"]
                            .sum().reset_index().sort_values(["año","mes"]))
                fig2 = px.bar(evol_llc, x="mes_nombre", y="monto_total_ars",
                              color_discrete_sequence=[C_INT], text_auto=".2s",
                              labels={"mes_nombre":"","monto_total_ars":"USD"})
                fig2.update_layout(showlegend=False, margin=dict(t=5,b=5))
                st.plotly_chart(fig2, use_container_width=True)
 
        # Por línea de negocio — segmentado por empresa
        st.markdown("#### Por línea de negocio — barras apiladas")
        linea_emp_col1, linea_emp_col2 = st.columns([2, 1])
        with linea_emp_col1:
            linea_emp_sel = st.radio(
                "Empresa para línea",
                ["TIARG S.A. (ARS)", "TIARG LLC (USD)", "Ambas"],
                horizontal=True, key="linea_emp", label_visibility="collapsed"
            )
        df_linea = df_sa if "S.A." in linea_emp_sel else (df_llc if "LLC" in linea_emp_sel else df)
        col_linea_monto = "monto_total_ars"
        if "linea_negocio" in df_linea.columns and not df_linea.empty:
            df_linea_plot = df_linea.copy()
            df_linea_plot["linea_plot"] = (
                df_linea_plot["linea_negocio"].astype(str).str.strip().str.upper().replace({"": "SIN LINEA"})
            )
            evol_l = (df_linea_plot.groupby(["mes","mes_nombre","linea_plot"])[col_linea_monto]
                      .sum().reset_index().sort_values("mes"))
            fig3 = px.bar(evol_l, x="mes_nombre", y=col_linea_monto,
                          color="linea_plot", barmode="stack",
                          color_discrete_map=COLORES_LINEA,
                          labels={"mes_nombre":"","monto_total_ars":"Monto","linea_plot":"Línea"})
            fig3.update_layout(margin=dict(t=5,b=5))
            st.plotly_chart(fig3, use_container_width=True)
        else:
            st.info("Sin datos de línea de negocio.")
 
        # Consolidado USD (Imp. usd) — tercer gráfico evolutivo
        st.markdown("#### Consolidado USD (Imp. usd) — todas las empresas")
        if not df.empty:
            evol_usd_consol = (df.groupby(["año","mes","mes_nombre"])["monto_usd"]
                               .sum().reset_index().sort_values(["año","mes"]))
            fig_uc = px.bar(evol_usd_consol, x="mes_nombre", y="monto_usd",
                            color_discrete_sequence=[C_TOTAL], text_auto=".2s",
                            labels={"mes_nombre":"","monto_usd":"USD"})
            fig_uc.update_layout(showlegend=False, margin=dict(t=5,b=5))
            st.plotly_chart(fig_uc, use_container_width=True)
 
        # Top 10 clientes + distribución — sincronizados por filtro de línea
        st.markdown("#### Top clientes · Distribución por línea")
        lineas_disp = sorted(df_ars["linea_negocio"].dropna().unique().tolist()) \
                      if "linea_negocio" in df_ars.columns and not df_ars.empty else []
        linea_sync = st.radio(
            "Filtrar por línea",
            ["Todas"] + lineas_disp,
            horizontal=True, key="linea_sync", label_visibility="collapsed"
        )
        df_sync = df_ars if linea_sync == "Todas" \
                  else df_ars[df_ars["linea_negocio"] == linea_sync] \
                       if "linea_negocio" in df_ars.columns else df_ars
 
        col_e, col_f = st.columns(2)
        with col_e:
            st.markdown(f"#### Top 10 clientes ARS{' · ' + linea_sync if linea_sync != 'Todas' else ''}")
            t10 = (df_sync.groupby("cliente")["monto_total_ars"].sum()
                   .nlargest(10).sort_values().reset_index())
            fig4 = px.bar(t10, x="monto_total_ars", y="cliente", orientation="h",
                          color_discrete_sequence=[color_p], text_auto=".2s",
                          labels={"monto_total_ars":"ARS","cliente":""})
            fig4.update_layout(showlegend=False, margin=dict(t=5,b=5,l=10))
            st.plotly_chart(fig4, use_container_width=True)
 
        with col_f:
            st.markdown(f"#### Distribución por línea{' · ' + linea_sync if linea_sync != 'Todas' else ''}")
            if "linea_negocio" in df_sync.columns:
                pie_l = df_sync.copy()
                pie_l["linea_plot"] = pie_l["linea_negocio"].astype(str).str.strip().str.upper().replace({"": "SIN LINEA"})
                pie_l = pie_l.groupby("linea_plot")["monto_total_ars"].sum().reset_index()
                fig5  = px.pie(pie_l, values="monto_total_ars", names="linea_plot",
                               color="linea_plot", color_discrete_map=COLORES_LINEA, hole=0.4)
                fig5.update_layout(margin=dict(t=5,b=5))
                st.plotly_chart(fig5, use_container_width=True)
 
 
# ══════════════════════════════════════════════
# TAB 3 — CUENTAS CORRIENTES
# ══════════════════════════════════════════════
with t3:
    if sin_cc:
        st.info("Sin datos de CC. Colocá cc_clientes.xlsx en data/raw/ y actualizá.")
    else:
        if "fuente_aging" in df_saldos.columns:
            fuentes = sorted(df_saldos["fuente_aging"].dropna().astype(str).unique().tolist())
            st.caption(f"Fuente de vencimiento activa: {', '.join(fuentes)}")

        deuda_total   = df_saldos[col_deuda_cc].sum()
        deuda_vencida = df_saldos["saldo_vencido"].sum()
        deuda_critica = df_saldos[df_saldos["aging"]=="+90 días"]["saldo_vencido"].sum()
        n_deudores    = len(df_saldos)
        mayor         = df_saldos[col_deuda_cc].max()
        desvio_abs_total = pd.to_numeric(df_saldos.get("dif_conciliacion", 0), errors="coerce").fillna(0).abs().sum()
        no_conciliados = 0
        if "conciliado" in df_saldos.columns:
            no_conciliados = int((~df_saldos["conciliado"].fillna(False)).sum())
 
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("Deuda total",      fmt_m(deuda_total))
        c2.metric("Deuda vencida",    fmt_m(deuda_vencida),
                  delta=f"{deuda_critica/deuda_vencida*100:.0f}% en +90" if deuda_vencida else None,
                  delta_color="inverse")
        c3.metric("Clientes deudores", str(n_deudores))
        c4.metric("Mayor saldo",       fmt_m(mayor))

        st.caption(f"Deuda crítica +90 días: {fmt_m(deuda_critica)}")
        st.caption(
            f"Conciliación contable · No conciliados: {no_conciliados} · Desvío acumulado: {fmt_m(desvio_abs_total)}"
        )

        kpis_fin = calcular_kpis_financieros(df, df_saldos)
        kf1, kf2, kf3, kf4 = st.columns(4)
        kf1.metric("DSO estimado", f"{kpis_fin['dso']:.0f} días")
        kf2.metric("% deuda vencida", f"{kpis_fin['overdue_ratio']:.1f}%")
        kf3.metric("Concentración Top 5", f"{kpis_fin['top5_concentracion']:.1f}%")
        kf4.metric("Cobertura vencida ≤30d", f"{kpis_fin['cobertura_30d']:.1f}%")
        st.caption(
            f"Facturación usada para DSO (últimos 90 días): {fmt_m(kpis_fin['facturacion_90d'])}"
        )

        st.markdown("---")

        # Alertas críticas luego de KPIs
        criticos = df_saldos[df_saldos["aging"] == "+90 días"].copy()
        st.markdown(f"#### 🚨 Alertas críticas ({len(criticos)})")
        if criticos.empty:
            st.success("No hay clientes con deuda vencida más de 90 días.")
        else:
            criticos_v = criticos[["Cliente", col_deuda_cc, "saldo_vencido", "dias_vencido", "dias_vencido_max",
                                   "total_facturado", "total_cobrado", "ratio_cobranza"]].copy()
            for c in [col_deuda_cc, "saldo_vencido", "total_facturado", "total_cobrado"]:
                criticos_v[c] = pd.to_numeric(criticos_v[c], errors="coerce").fillna(0).map(lambda x: f"$ {x:,.0f}")

            st.dataframe(
                criticos_v.rename(columns={
                    col_deuda_cc:"Saldo actual","saldo_vencido":"Saldo vencido",
                    "dias_vencido":"Días pond.","dias_vencido_max":"Máx. días",
                    "total_facturado":"Total facturado","total_cobrado":"Total cobrado",
                    "ratio_cobranza":"% Cobrado"
                }),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "% Cobrado": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%.0f%%"),
                }
            )

            st.markdown("##### 📄 Comprobantes/documentos pendientes por cliente crítico")
            cli_crit = st.selectbox(
                "Cliente crítico",
                criticos["Cliente"].dropna().tolist(),
                key="cli_critico_cc",
            )

            if df_cc_mov is not None and "Cliente" in df_cc_mov.columns:
                mov_crit = df_cc_mov[df_cc_mov["Cliente"] == cli_crit].copy()
                saldo_col = "Saldo ppal" if "Saldo ppal" in mov_crit.columns else None
                if saldo_col:
                    mov_crit[saldo_col] = pd.to_numeric(mov_crit[saldo_col], errors="coerce")
                    mov_crit = mov_crit[mov_crit[saldo_col] > 0]

                cols_crit = [
                    "Fecha", "Documento", "Descripción", "Fecha vencimiento",
                    "Debe ppal", "Haber ppal", "Saldo ppal", "tipo",
                ]
                cols_crit = [c for c in cols_crit if c in mov_crit.columns]

                if mov_crit.empty:
                    st.info("No se encontraron comprobantes pendientes para este cliente crítico.")
                else:
                    mov_crit_v = mov_crit[cols_crit].copy()
                    for c in ["Debe ppal", "Haber ppal", "Saldo ppal"]:
                        if c in mov_crit_v.columns:
                            mov_crit_v[c] = pd.to_numeric(mov_crit_v[c], errors="coerce").fillna(0).map(lambda x: f"$ {x:,.0f}")

                    st.dataframe(
                        mov_crit_v.sort_values("Fecha", ascending=False) if "Fecha" in mov_crit_v.columns else mov_crit_v,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Fecha": st.column_config.DateColumn("Fecha"),
                            "Fecha vencimiento": st.column_config.DateColumn("Vencimiento"),
                        },
                    )
 
        st.markdown("---")
        col_a, col_b = st.columns(2)
 
        with col_a:
            st.markdown("#### Aging de deuda")
            aging_df = (df_saldos.groupby("aging")[col_deuda_cc]
                        .sum().reindex(AGING_ORDEN).dropna().reset_index())
            fig6 = px.bar(aging_df, x="aging", y=col_deuda_cc,
                          color="aging", color_discrete_map=AGING_COLOR,
                          labels={"aging":"", col_deuda_cc:"ARS"}, text_auto=".2s")
            fig6.update_layout(showlegend=False, margin=dict(t=5,b=5))
            st.plotly_chart(fig6, use_container_width=True)
 
        with col_b:
            st.markdown("#### Top 10 deudores")
            top10 = df_saldos.head(10)[["Cliente", col_deuda_cc, "saldo_vencido", "dias_vencido", "aging"]]
            fig7  = px.bar(top10.sort_values(col_deuda_cc), x=col_deuda_cc, y="Cliente",
                           orientation="h", color="aging", color_discrete_map=AGING_COLOR,
                           labels={col_deuda_cc:"ARS","Cliente":""}, text_auto=".2s")
            fig7.update_layout(showlegend=True, margin=dict(t=5,b=5,l=10))
            st.plotly_chart(fig7, use_container_width=True)

        st.markdown("#### Matriz de riesgo de cobranza")
        riesgo = df_saldos.copy()
        riesgo["dias_vencido"] = pd.to_numeric(riesgo.get("dias_vencido", 0), errors="coerce").fillna(0)
        riesgo["saldo_vencido"] = pd.to_numeric(riesgo.get("saldo_vencido", 0), errors="coerce").fillna(0)
        riesgo["saldo_actual"] = pd.to_numeric(riesgo.get(col_deuda_cc, 0), errors="coerce").fillna(0)
        riesgo = riesgo[riesgo["saldo_actual"] > 0].copy()
        riesgo["segmento_riesgo"] = pd.cut(
            riesgo["dias_vencido"],
            bins=[-1, 0, 30, 60, 90, 10_000],
            labels=["Al día", "1-30", "31-60", "61-90", "+90"],
        )
        fig_riesgo = px.scatter(
            riesgo,
            x="dias_vencido",
            y="saldo_vencido",
            size="saldo_actual",
            color="segmento_riesgo",
            hover_name="Cliente",
            hover_data={"saldo_actual": ":,.0f", "ratio_cobranza": ":.1f"},
            color_discrete_map={
                "Al día": C_VERDE,
                "1-30": "#84cc16",
                "31-60": "#f59e0b",
                "61-90": "#f97316",
                "+90": C_ROJO,
            },
            labels={"dias_vencido": "Días vencido", "saldo_vencido": "Saldo vencido ARS"},
        )
        fig_riesgo.add_vline(x=90, line_dash="dot", line_color=C_ROJO)
        fig_riesgo.update_layout(height=420, margin=dict(t=10, b=10, l=10, r=10))
        st.plotly_chart(fig_riesgo, use_container_width=True)

        if not sin_comp and df_cc_comp is not None and not df_cc_comp.empty and "centro_costo" in df_cc_comp.columns:
            st.markdown("#### Deuda por centro de costo (composición)")
            deuda_centros = (
                df_cc_comp.groupby("centro_costo", as_index=False)["saldo_abierto"]
                .sum()
                .sort_values("saldo_abierto", ascending=False)
                .head(15)
            )
            fig_centros = px.bar(
                deuda_centros.sort_values("saldo_abierto"),
                x="saldo_abierto",
                y="centro_costo",
                orientation="h",
                color_discrete_sequence=[C_TOTAL],
                labels={"saldo_abierto": "ARS", "centro_costo": ""},
                text_auto=".2s",
            )
            fig_centros.update_layout(showlegend=False, margin=dict(t=5, b=5, l=10), height=360)
            st.plotly_chart(fig_centros, use_container_width=True)

        if "dif_conciliacion" in df_saldos.columns:
            st.markdown("#### Control de conciliación de saldos")
            conciliacion_df = df_saldos[[
                "Cliente", "saldo_inicial", "debe_total", "haber_total",
                "saldo_reconstruido", "saldo_actual", "dif_conciliacion", "conciliado"
            ]].copy()
            conciliacion_df["dif_abs"] = pd.to_numeric(
                conciliacion_df["dif_conciliacion"], errors="coerce"
            ).fillna(0).abs()
            conciliacion_df = conciliacion_df.sort_values("dif_abs", ascending=False)

            desfasados = conciliacion_df[conciliacion_df["dif_abs"] > 1].copy()
            if desfasados.empty:
                st.success("Saldos conciliados: saldo_final = saldo_inicial + debe - haber (tolerancia $1).")
            else:
                st.warning(f"Se detectaron {len(desfasados)} clientes con desvío de conciliación mayor a $1.")
                st.dataframe(
                    desfasados[[
                        "Cliente", "saldo_inicial", "debe_total", "haber_total",
                        "saldo_reconstruido", "saldo_actual", "dif_conciliacion"
                    ]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "saldo_inicial": st.column_config.NumberColumn("Saldo inicial", format="$ %,.0f"),
                        "debe_total": st.column_config.NumberColumn("Debe", format="$ %,.0f"),
                        "haber_total": st.column_config.NumberColumn("Haber", format="$ %,.0f"),
                        "saldo_reconstruido": st.column_config.NumberColumn("Saldo reconstruido", format="$ %,.0f"),
                        "saldo_actual": st.column_config.NumberColumn("Saldo final", format="$ %,.0f"),
                        "dif_conciliacion": st.column_config.NumberColumn("Desvío", format="$ %,.2f"),
                    },
                )
 
        # Ratio de cobranza
        st.markdown("#### Ratio de cobranza por cliente")
        ratio_df = df_saldos[["Cliente","total_facturado","total_cobrado", col_deuda_cc, "ratio_cobranza"]].copy()
        ratio_df = ratio_df.rename(columns={col_deuda_cc: "saldo_actual"})
        ratio_df["cobrado_pct"] = ratio_df["ratio_cobranza"]
        fig8 = px.bar(ratio_df.sort_values("cobrado_pct"), x="cobrado_pct", y="Cliente",
                      orientation="h", color="cobrado_pct",
                      color_continuous_scale=["#ef4444","#f59e0b","#22c55e"],
                      range_color=[0,100],
                      labels={"cobrado_pct":"% Cobrado","Cliente":""},
                      text_auto=".0f")
        fig8.update_layout(margin=dict(t=5,b=5,l=10), coloraxis_showscale=False)
        st.plotly_chart(fig8, use_container_width=True)

        csv_cc = df_saldos.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Exportar CC", csv_cc, "cc_saldos.csv", "text/csv")
 
 
# ══════════════════════════════════════════════
# TAB 4 — CLIENTES (cruce facturación + CC)
# ══════════════════════════════════════════════
with t4:
    st.markdown("#### Vista cruzada: Facturación vs. Deuda por cliente")
 
    if df_ars.empty and sin_cc:
        st.info("Se necesitan ambos archivos para esta vista.")
    else:
        # Facturado por cliente
        if not df_ars.empty:
            fact_cli = (df_ars.groupby("cliente")["monto_total_ars"]
                        .sum().reset_index()
                        .rename(columns={"cliente":"Cliente","monto_total_ars":"Facturado ARS"}))
        else:
            fact_cli = pd.DataFrame(columns=["Cliente","Facturado ARS"])
 
        # Cruzar con saldos
        if not sin_cc:
            cruce = fact_cli.merge(
                df_saldos[["Cliente", col_deuda_cc, "saldo_vencido", "aging", "dias_vencido", "ratio_cobranza"]].rename(columns={col_deuda_cc: "saldo_actual"}),
                on="Cliente", how="outer"
            )
            for col in ["Facturado ARS", "saldo_actual", "saldo_vencido", "dias_vencido", "ratio_cobranza"]:
                if col in cruce.columns:
                    cruce[col] = pd.to_numeric(cruce[col], errors="coerce").fillna(0)
            if "aging" in cruce.columns:
                cruce["aging"] = cruce["aging"].fillna("Sin deuda")
            cruce = cruce.rename(columns={"saldo_actual":"Deuda ARS"})
            cruce = cruce.sort_values("Facturado ARS", ascending=False)
        else:
            cruce = fact_cli.copy()
            cruce["Deuda ARS"] = 0
 
        # Matriz de clientes: facturacion vs deuda, mas legible que barras agrupadas
        st.markdown("#### Mapa de clientes")
        cruce_plot = cruce.copy()
        cruce_plot["Estado"] = cruce_plot["aging"] if "aging" in cruce_plot.columns else "Sin deuda"
        cruce_plot["tamano"] = cruce_plot[["Facturado ARS", "Deuda ARS"]].max(axis=1).clip(lower=1)

        fig9 = px.scatter(
            cruce_plot,
            x="Facturado ARS",
            y="Deuda ARS",
            color="Estado",
            size="tamano",
            size_max=26,
            hover_name="Cliente",
            hover_data={
                "Facturado ARS": ":,.0f",
                "Deuda ARS": ":,.0f",
                "saldo_vencido": ":,.0f",
                "dias_vencido": True,
                "ratio_cobranza": ":.0f",
                "tamano": False,
            },
            color_discrete_map={**AGING_COLOR, "Sin deuda": "#94a3b8"},
            labels={
                "Facturado ARS": "Facturado ARS",
                "Deuda ARS": "Deuda ARS",
                "saldo_vencido": "Saldo vencido",
                "dias_vencido": "Días vencido",
                "ratio_cobranza": "% Cobrado",
            },
        )
        fig9.add_hline(y=cruce_plot["Deuda ARS"].median(), line_dash="dot", line_color="#94a3b8")
        fig9.add_vline(x=cruce_plot["Facturado ARS"].median(), line_dash="dot", line_color="#94a3b8")
        fig9.update_traces(
            marker=dict(line=dict(width=1, color="white"), opacity=0.82),
            selector=dict(mode="markers")
        )
        fig9.update_layout(
            margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", y=1.05),
            xaxis_tickformat=",.0f",
            yaxis_tickformat=",.0f",
            height=460,
        )
        st.plotly_chart(fig9, use_container_width=True)
 
        # Tabla resumen
        st.markdown("#### Tabla resumen")
        cols_tabla = ["Cliente","Facturado ARS","Deuda ARS","saldo_vencido","ratio_cobranza","aging","dias_vencido"]
        cols_tabla = [c for c in cols_tabla if c in cruce.columns]
        st.dataframe(
            cruce[cols_tabla].rename(columns={
                "saldo_vencido":"Saldo vencido","ratio_cobranza":"% Cobrado",
                "aging":"Estado","dias_vencido":"Días vencido"
            }),
            use_container_width=True, hide_index=True,
            column_config={
                "Facturado ARS": st.column_config.NumberColumn(format="$ %.0f"),
                "Deuda ARS":     st.column_config.NumberColumn(format="$ %.0f"),
                "Saldo vencido": st.column_config.NumberColumn(format="$ %.0f"),
                "% Cobrado":     st.column_config.ProgressColumn(min_value=0,max_value=100,format="%.0f%%"),
            }
        )
 
 
# ══════════════════════════════════════════════
# TAB 5 — ASISTENTE IA
# ══════════════════════════════════════════════
with t5:
    st.markdown("### 🤖 Asistente financiero IA")
    st.markdown(
        "Hacé preguntas sobre los datos del dashboard. "
        "El modelo corre localmente con Ollama — **los datos nunca salen de tu red**."
    )
 
    if not ollama_disponible():
        st.warning("⚠️ Ollama no está corriendo. Inicialo con `ollama serve` y recargá la página.")
    else:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
 
        from dashboard.asistente import generar_contexto, consultar_ollama
        contexto = generar_contexto(
            facturas_df=df if not df.empty else None,
            cc_df=df_saldos if not sin_cc else None,
            empresa=empresa,
            moneda="ARS",
        )
 
        for msg in st.session_state.chat_history:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
 
        if prompt := st.chat_input("Preguntá sobre facturación, deuda, clientes..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Analizando..."):
                    respuesta = consultar_ollama(st.session_state.chat_history, contexto)
                st.markdown(respuesta)
            st.session_state.chat_history.append({"role": "assistant", "content": respuesta})
 
        if st.session_state.get("chat_history"):
            if st.button("🗑️ Limpiar conversación"):
                st.session_state.chat_history = []
                st.rerun()
 
 
# ══════════════════════════════════════════════
# TAB 6 — DETALLE
# ══════════════════════════════════════════════
with t6:
    sub1, sub2 = st.tabs(["📄 Comprobantes de facturación", "📒 Movimientos CC"])
 
    with sub1:
        if sin_fact or df.empty:
            st.info("Sin datos de facturación.")
        else:
            clientes_l = ["Todos"] + sorted(df["cliente"].dropna().unique().tolist())
            cli_sel    = st.selectbox("Cliente", clientes_l, key="cli_fact")
            df_t = df if cli_sel == "Todos" else df[df["cliente"] == cli_sel]
 
            cols = ["fecha","tipo_documento","numero_comprobante","cliente","razon_social",
                    "descripcion","linea_negocio","moneda_iso","monto_neto_ars","monto_total_ars",
                    "monto_usd","importe_pendiente","condicion_pago"]
            cols = [c for c in cols if c in df_t.columns]
            st.dataframe(df_t[cols].sort_values("fecha", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "fecha":            st.column_config.DateColumn("Fecha"),
                    "monto_neto_ars":   st.column_config.NumberColumn("Neto ARS",   format="$ %.0f"),
                    "monto_total_ars":  st.column_config.NumberColumn("Total ARS",  format="$ %.0f"),
                    "monto_usd":        st.column_config.NumberColumn("USD",        format="USD %.2f"),
                    "importe_pendiente":st.column_config.NumberColumn("Pendiente",  format="$ %.0f"),
                })
            csv = df_t[cols].to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Exportar", csv, "comprobantes.csv", "text/csv")
 
    with sub2:
        if df_cc_mov is None:
            st.info("Sin movimientos de CC.")
        else:
            df_cc_mov["Fecha"] = pd.to_datetime(df_cc_mov["Fecha"], errors="coerce")
            clientes_cc = ["Todos"] + sorted(df_cc_mov["Cliente"].dropna().unique().tolist())
            cli_cc = st.selectbox("Cliente", clientes_cc, key="cli_cc")
            df_mov_f = df_cc_mov if cli_cc == "Todos" else df_cc_mov[df_cc_mov["Cliente"] == cli_cc]
 
            cols_cc = ["Fecha","Documento","Cliente","Descripción","Debe ppal","Haber ppal","Saldo ppal","Fecha vencimiento","tipo"]
            cols_cc = [c for c in cols_cc if c in df_mov_f.columns]
            st.dataframe(
                df_mov_f[cols_cc].sort_values("Fecha", ascending=False),
                use_container_width=True, hide_index=True,
                column_config={
                    "Fecha":            st.column_config.DateColumn("Fecha"),
                    "Fecha vencimiento":st.column_config.DateColumn("Vencimiento"),
                    "Debe ppal":        st.column_config.NumberColumn("Debe",   format="$ %.0f"),
                    "Haber ppal":       st.column_config.NumberColumn("Haber",  format="$ %.0f"),
                    "Saldo ppal":       st.column_config.NumberColumn("Saldo",  format="$ %.0f"),
                }
            )