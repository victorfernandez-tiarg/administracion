
"""
Finnegans BI — Dashboard Híbrido
Facturación + Cuentas Corrientes reales de Finnegans GO
"""
 
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import plotly.io as pio
from pathlib import Path
import os
import io
import json, sys
import unicodedata
from datetime import date, datetime
 
#streamlit run dashboard/app.py 
sys.path.append(str(Path(__file__).parent.parent))
from etl.procesar    import correr_etl
from etl.procesar_cc import correr_etl_cc, calcular_aging
from etl.sync_drive  import sincronizar
from etl.db          import cargar as db_cargar, cargar_meta as db_cargar_meta, cargar_permisos as db_cargar_permisos, guardar_permisos as db_guardar_permisos
 
 
 
RAW_DIR = Path("data/raw")
PROCESSED_DIR = Path("data/processed")
ASSETS_DIR = Path(__file__).parent / "assets"
UI_STATE_PATH = PROCESSED_DIR / "ui_state.json"
 
st.set_page_config(page_title="tiarg", page_icon=str(ASSETS_DIR / "logo_empresa.png"), layout="wide")
 
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
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Sora:wght@600;700;800&display=swap');

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
        font-family: 'IBM Plex Sans', 'Segoe UI', Arial, sans-serif;
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
        color: #cbd5e1 !important;
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
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(148,163,184,0.35);
        box-shadow: none;
    }}

    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stDownloadButton > button {{
        background: rgba(255,255,255,0.16);
        color: var(--sidebar-text);
        border: 1px solid rgba(148,163,184,0.35);
    }}

    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {{
        background: rgba(15, 23, 42, 0.55);
        border: 1px dashed rgba(148, 163, 184, 0.55);
        border-radius: 12px;
    }}

    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {{
        color: #e5eef8 !important;
    }}

    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] span,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploader"] span {{
        color: #cbd5e1 !important;
    }}

    [data-testid="stSidebar"] .stButton > button[kind="primary"] {{
        background: linear-gradient(90deg, #0284c7 0%, #0ea5e9 100%);
        color: #ffffff;
        border-color: rgba(14,165,233,0.95);
    }}

    .block-container {{
        padding-top: 5.6rem;
        padding-bottom: 2.2rem;
    }}

    h1, h2, h3, h4 {{
        color: var(--text);
        letter-spacing: -0.02em;
        font-family: 'Sora', 'Segoe UI', Arial, sans-serif;
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
        font-family: 'Sora', 'Segoe UI', Arial, sans-serif;
    }}

    [data-testid="stMetricDelta"] {{
        font-weight: 600;
    }}

    [data-testid="stExpander"],
    div[data-baseweb="select"],
    div[data-baseweb="input"],
    [data-testid="stDateInput"] > div {{
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
        position: sticky;
        top: 0.35rem;
        z-index: 999;
        background: rgba(248, 250, 252, 0.82);
        backdrop-filter: blur(8px);
        padding-top: 0.15rem;
    }}

    div[data-testid="stTabs"] > div {{
        overflow: visible !important;
    }}

    div[data-testid="stTabs"]:first-of-type {{
        width: 100%;
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
        font-family: 'Sora', 'Segoe UI', Arial, sans-serif;
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

    @media (max-width: 900px) {{
        .block-container {{
            padding-top: 5.1rem;
            padding-left: 0.7rem;
            padding-right: 0.7rem;
        }}

        .mobile-stack div[data-testid="stHorizontalBlock"] {{
            flex-direction: column !important;
            gap: 0.6rem !important;
        }}

        .mobile-stack div[data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
            width: 100% !important;
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }}

        .stTabs [data-baseweb="tab"] {{
            padding: 0.4rem 0.75rem;
            font-size: 0.9rem;
        }}
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

# ── Login ───────────────────────────────────────────
import hashlib

def _get_auth_config() -> tuple[str, dict]:
    """
    Devuelve (salt, {usuario: hash}).
    Prioridad: st.secrets → variables de entorno.
    Variables de entorno:
        AUTH_SALT   = "el_salt"
        AUTH_USERS  = "admin:hash1,usuario2:hash2"
    """
    salt = ""
    users: dict = {}

    # 1) Intentar st.secrets (local / .streamlit/secrets.toml)
    try:
        salt = st.secrets.get("auth", {}).get("salt", "")
        users = dict(st.secrets.get("users", {}))
    except FileNotFoundError:
        pass

    # 2) Fallback: variables de entorno (Railway / Docker)
    if not salt:
        salt = os.getenv("AUTH_SALT", "")
    if not users:
        raw = os.getenv("AUTH_USERS", "")          # formato: "admin:hash1,user2:hash2"
        for entry in raw.split(","):
            entry = entry.strip()
            if ":" in entry:
                u, h = entry.split(":", 1)
                users[u.strip()] = h.strip()

    return salt, users


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000).hex()


def _check_credentials(username: str, password: str) -> bool:
    salt, users = _get_auth_config()
    expected = users.get(username)
    if not expected or not salt:
        return False
    return expected == _hash_password(password, salt)

def _login_page():
    st.markdown("""
    <style>
    /* Ocultar sidebar en el login */
    [data-testid="stSidebar"] { display: none !important; }
    .block-container { padding-top: 6rem !important; }
    .login-card {
        max-width: 400px;
        margin: 0 auto;
        background: rgba(255,255,255,0.92);
        border: 1px solid #dbe4f0;
        border-radius: 22px;
        padding: 2.5rem 2rem 2rem 2rem;
        box-shadow: 0 18px 50px rgba(15,23,42,0.08);
    }
    .login-title {
        font-family: 'Sora', 'Segoe UI', Arial, sans-serif;
        font-size: 1.6rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.03em;
        margin-bottom: 0.25rem;
    }
    .login-sub {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    col_l, col_c, col_r = st.columns([1, 2, 1])
    with col_c:
        logo_path = ASSETS_DIR / "logo_empresa.png"
        if logo_path.exists():
            st.image(str(logo_path), width=160)
        st.markdown('<div class="login-title">Acceso al dashboard</div>', unsafe_allow_html=True)
        st.markdown('<div class="login-sub">Ingresá con tus credenciales</div>', unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            usuario = st.text_input("Usuario", placeholder="nombre de usuario")
            password = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submitted = st.form_submit_button("Ingresar", use_container_width=True)

        if submitted:
            if _check_credentials(usuario.strip(), password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = usuario.strip()
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")

# Verificar autenticación antes de mostrar cualquier cosa
if not st.session_state.get("authenticated"):
    _login_page()
    st.stop()

# ── Permisos ───────────────────────────────────────
_PERMISOS_PATH = Path(__file__).parent / "permisos.json"

def _cargar_permisos() -> dict:
    return db_cargar_permisos()

def _guardar_permisos(perms: dict) -> bool:
    return db_guardar_permisos(perms)
_permisos_global   = _cargar_permisos()
_username_actual   = st.session_state.get("username", "")
_es_superusuario   = _username_actual in _permisos_global.get("superusers", [])
_perms_usuario     = _permisos_global.get("users", {}).get(_username_actual, {})
# Listas de permisos para el usuario actual (vacío = sin restricción)
_clientes_perm      = [c.strip().title() for c in _perms_usuario.get("clientes", [])]
_clientes_perm_modo = _perms_usuario.get("clientes_modo", "Excluir")   # "Incluir" o "Excluir"
_centros_perm       = [c.strip()         for c in _perms_usuario.get("centros",  [])]
_centros_perm_modo  = _perms_usuario.get("centros_modo",  "Excluir")
_tabs_perm          = [t.strip()         for t in _perms_usuario.get("tabs",     [])]

# ── Helpers ────────────────────────────────────────
@st.cache_data(show_spinner=False)
def load(nombre):
    return db_cargar(nombre)
 
def fmt_m(v, moneda="ARS"):
    if moneda == "USD":
        return f"USD {v:,.0f}"
    return f"$ {v:,.0f}"


def abrir_bloque_mobile_stack():
    st.markdown('<div class="mobile-stack">', unsafe_allow_html=True)


def cerrar_bloque_mobile_stack():
    st.markdown("</div>", unsafe_allow_html=True)


def cargar_estado_ui_global():
    if not UI_STATE_PATH.exists():
        return {}
    try:
        with open(UI_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def guardar_estado_ui_global(estado):
    try:
        UI_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(UI_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(estado, f, ensure_ascii=False, indent=2)
    except Exception:
        # Si no se puede persistir estado, la app debe seguir funcionando.
        pass


def parsear_fecha_iso(valor):
    if not valor or not isinstance(valor, str):
        return None
    try:
        return date.fromisoformat(valor)
    except Exception:
        return None
 
@st.cache_data(show_spinner=False)
def load_meta():
    return db_cargar_meta()


def _normalizar_columna(nombre: str) -> str:
    base = unicodedata.normalize("NFKD", str(nombre).strip())
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    return "".join(ch.lower() for ch in base if ch.isalnum())


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
    tokens_cliente = ("cliente", "razonsocial", "razon", "social")
    tokens_saldo = ("saldoabierto", "saldo", "importependiente", "pendiente", "deuda", "importe")

    try:
        xls = pd.ExcelFile(io.BytesIO(archivo_bytes))
    except Exception as e:
        return False, f"No se pudo leer Excel: {e}"

    ejemplos_cols = []
    for sheet in xls.sheet_names:
        for header_row in range(0, 6):
            try:
                df_cols = pd.read_excel(
                    io.BytesIO(archivo_bytes),
                    sheet_name=sheet,
                    header=header_row,
                    nrows=0,
                )
            except Exception:
                continue

            cols = [str(c) for c in df_cols.columns.astype(str).tolist() if str(c).strip()]
            if not cols:
                continue
            cols_norm = [_normalizar_columna(c) for c in cols]
            if not ejemplos_cols:
                ejemplos_cols = cols[:8]

            tiene_cliente = any(any(tok in c for tok in tokens_cliente) for c in cols_norm)
            tiene_saldo = any(any(tok in c for tok in tokens_saldo) for c in cols_norm)
            if tiene_cliente and tiene_saldo:
                return True, "OK"

    detalle = f" Columnas detectadas (ejemplo): {', '.join(ejemplos_cols)}" if ejemplos_cols else ""
    return False, "No se detectaron columnas de cliente y saldo en ninguna hoja." + detalle


def _guardar_adjunto_en_raw(uploaded_file, destino: Path) -> int:
    contenido = uploaded_file.getvalue()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(contenido)
    return len(contenido)


def _archivo_composicion_raw() -> Path | None:
    candidatos = [
        RAW_DIR / "composicion_saldos.xlsx",
        RAW_DIR / "composicion_de_saldos.xlsx",
        RAW_DIR / "cc_composicion.xlsx",
    ]
    for p in candidatos:
        if p.exists():
            return p
    for patron in ("*composicion*.xlsx", "*composición*.xlsx", "Reporte*.xlsx", "*saldos*.xlsx"):
        for p in sorted(RAW_DIR.glob(patron)):
            if p.name.lower() != "cc_clientes.xlsx":
                return p
    return None


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

# Aplicar restricciones de permisos para usuarios regulares
if not _es_superusuario:
    if _clientes_perm:
        _set_cli = set(_clientes_perm)
        if _clientes_perm_modo == "Excluir":
            clientes_opts = [c for c in clientes_opts if c.strip().title() not in _set_cli]
        else:
            clientes_opts = [c for c in clientes_opts if c.strip().title() in _set_cli]
    if _centros_perm:
        _set_ctr = set(_centros_perm)
        if _centros_perm_modo == "Excluir":
            centros_opts = [c for c in centros_opts if c.strip() not in _set_ctr]
        else:
            centros_opts = [c for c in centros_opts if c.strip() in _set_ctr]

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

    # Usuario activo + cerrar sesión
    username_display = st.session_state.get("username", "")
    st.markdown(
        f'<div style="font-size:0.78rem;color:#94a3b8;margin-bottom:0.4rem;">👤 {username_display}</div>',
        unsafe_allow_html=True,
    )
    if st.button("Cerrar sesión", key="btn_logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

    st.markdown("---")

    st.markdown("**Navegación**")
    if "tab_nav" not in st.session_state:
        st.session_state["tab_nav"] = "Facturación"

    nav_css = """
    <style>
    .nav-vertical .stButton > button {
        width: 100% !important;
        border-radius: 6px !important;
        min-height: 42px !important;
        padding: 0.45rem 0.75rem !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        text-align: left !important;
        transition: all 0.18s ease !important;
    }

    .nav-vertical .stButton > button[kind="secondary"] {
        background: rgba(255, 255, 255, 0.02) !important;
        color: #d2d8e4 !important;
        border: 1px solid rgba(255, 255, 255, 0.14) !important;
        box-shadow: none !important;
    }

    .nav-vertical .stButton > button[kind="secondary"]:hover {
        background: rgba(63, 126, 255, 0.12) !important;
        border-color: rgba(63, 126, 255, 0.42) !important;
        color: #eef3ff !important;
    }

    .nav-vertical .stButton > button[kind="primary"] {
        background: #2d7ff9 !important;
        color: #ffffff !important;
        border: 1px solid #2d7ff9 !important;
        box-shadow: 0 6px 18px rgba(45, 127, 249, 0.26) !important;
    }

    .nav-vertical .stButton > button[kind="primary"]:hover {
        background: #2372ea !important;
        border-color: #2372ea !important;
    }
    </style>
    """
    st.markdown(nav_css, unsafe_allow_html=True)

    opciones_nav = ["Facturación", "CC", "Clientes"]
    if _es_superusuario:
        opciones_nav.append("Admin")
    # Filtrar tabs según permisos (vacío = todas)
    if not _es_superusuario and _tabs_perm:
        opciones_nav = [t for t in opciones_nav if t in _tabs_perm]
        if st.session_state.get("tab_nav") not in opciones_nav and opciones_nav:
            st.session_state["tab_nav"] = opciones_nav[0]
    st.markdown('<div class="nav-vertical">', unsafe_allow_html=True)
    for opcion in opciones_nav:
        es_activa = st.session_state.get("tab_nav") == opcion
        if st.button(
            opcion,
            key=f"nav_btn_{opcion}",
            use_container_width=True,
            type="primary" if es_activa else "secondary",
        ):
            if st.session_state.get("tab_nav") != opcion:
                st.session_state["tab_nav"] = opcion
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("**Última actualización**")
    meta = load_meta()
    if meta and "ultima_actualizacion" in meta:
        try:
            dt_str = meta["ultima_actualizacion"]
            dt_obj = datetime.fromisoformat(dt_str)
            fecha_fmt = dt_obj.strftime("%d/%m/%Y")
            hora_fmt = dt_obj.strftime("%H:%M:%S")
            st.caption(f"📅 {fecha_fmt}")
            st.caption(f"🕐 {hora_fmt}")
            if "filas" in meta:
                st.caption(f"📊 {meta['filas']:,} registros")
        except Exception:
            st.caption("Información no disponible")
    else:
        st.caption("Sin actualización registrada")

    st.markdown("---")

    st.markdown("**Carga de archivos**")
    if "adjuntos_status" in st.session_state:
        st.success(st.session_state.pop("adjuntos_status"))

    comp_raw_actual = _archivo_composicion_raw()
    if comp_raw_actual is None:
        st.caption("Composición raw: no detectada")
    else:
        st.caption(f"Composición raw detectada: {comp_raw_actual.name}")

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

    if st.button("Validar y procesar adjuntos", type="primary"):
        if up_fact is None and up_cc is None and up_comp is None:
            st.warning("Adjuntá al menos un archivo para procesar.")
        else:
            errores = []
            advertencias = []
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
                _guardar_adjunto_en_raw(up_comp, RAW_DIR / "composicion_saldos.xlsx")
                guardados.append("Composición")
                if not ok:
                    advertencias.append(
                        "Composición: validación flexible no concluyente; se guardó igual y se intentó procesar con ETL. "
                        + msg
                    )

            if errores:
                st.error("No se pudo procesar por validaciones:\n- " + "\n- ".join(errores))
            else:
                with st.spinner("Validado. Procesando archivos adjuntos..."):
                    facturas = correr_etl(sync_drive=False)
                    _, saldos = correr_etl_cc(sync_drive=False)

                if advertencias:
                    st.warning("\n".join(advertencias))

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

    if st.button("Sincronizar Drive"):
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

    if st.button("Reprocesar todo", type="primary"):
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
        if st.button("Facturación", type="primary"):
            with st.spinner("Procesando..."):
                facturas = correr_etl()
            if facturas is None:
                st.error("ETL de facturación falló. Revisá el archivo local y los logs.")
            else:
                st.cache_data.clear(); st.rerun()
    with col2:
        if st.button("Ctas. Ctes.", type="primary"):
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
# ── Período global — justo debajo del navbar ────
st.markdown("### Período global")

estado_ui_global = cargar_estado_ui_global()

# Inicializar session_state con valores válidos dentro del rango disponible
fecha_desde_default = max(fecha_min_default, date(fecha_max_default.year, 1, 1))
fecha_hasta_default = fecha_max_default

fecha_desde_persistida = parsear_fecha_iso(estado_ui_global.get("fecha_desde"))
fecha_hasta_persistida = parsear_fecha_iso(estado_ui_global.get("fecha_hasta"))

if fecha_desde_persistida is not None:
    fecha_desde_persistida = min(max(fecha_desde_persistida, fecha_min_default), fecha_max_default)
if fecha_hasta_persistida is not None:
    fecha_hasta_persistida = min(max(fecha_hasta_persistida, fecha_min_default), fecha_max_default)

if "fecha_desde" not in st.session_state or not isinstance(st.session_state["fecha_desde"], date):
    st.session_state["fecha_desde"] = fecha_desde_persistida or fecha_desde_default
else:
    # Asegurar que el valor está dentro del rango disponible
    st.session_state["fecha_desde"] = min(max(st.session_state["fecha_desde"], fecha_min_default), fecha_max_default)

if "fecha_hasta" not in st.session_state or not isinstance(st.session_state["fecha_hasta"], date):
    st.session_state["fecha_hasta"] = fecha_hasta_persistida or fecha_hasta_default
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
    st.warning("Fecha desde > hasta, se invirtieron.")
    fecha_desde, fecha_hasta = fecha_hasta, fecha_desde

st.markdown("### Filtros globales")

if "modo_filtro_clientes" not in st.session_state:
    modo_cli_persistido = estado_ui_global.get("modo_filtro_clientes", "Incluir seleccionados")
    st.session_state["modo_filtro_clientes"] = (
        modo_cli_persistido if modo_cli_persistido in ["Incluir seleccionados", "Excluir seleccionados"] else "Incluir seleccionados"
    )

if "modo_filtro_centros" not in st.session_state:
    modo_ctr_persistido = estado_ui_global.get("modo_filtro_centros", "Incluir seleccionados")
    st.session_state["modo_filtro_centros"] = (
        modo_ctr_persistido if modo_ctr_persistido in ["Incluir seleccionados", "Excluir seleccionados"] else "Incluir seleccionados"
    )

if "filtro_global_clientes" not in st.session_state:
    clientes_persistidos = estado_ui_global.get("filtro_global_clientes", [])
    if not isinstance(clientes_persistidos, list):
        clientes_persistidos = []
    clientes_validos = set(clientes_opts)
    st.session_state["filtro_global_clientes"] = [c for c in clientes_persistidos if c in clientes_validos]

if "filtro_global_centros" not in st.session_state:
    centros_persistidos = estado_ui_global.get("filtro_global_centros", [])
    if not isinstance(centros_persistidos, list):
        centros_persistidos = []
    centros_validos = set(centros_opts)
    st.session_state["filtro_global_centros"] = [c for c in centros_persistidos if c in centros_validos]

abrir_bloque_mobile_stack()
f1, f2 = st.columns(2)

if _es_superusuario:
    with f1:
        modo_clientes = st.radio(
            "Modo clientes",
            ["Incluir seleccionados", "Excluir seleccionados"],
            horizontal=True,
            key="modo_filtro_clientes",
        )
        clientes_sel = st.multiselect("Clientes", clientes_opts, key="filtro_global_clientes")

    with f2:
        modo_centros = st.radio(
            "Modo centros",
            ["Incluir seleccionados", "Excluir seleccionados"],
            horizontal=True,
            key="modo_filtro_centros",
        )
        centros_sel = st.multiselect("Centros de costo", centros_opts, key="filtro_global_centros")
else:
    # Usuario regular: vista bloqueada a sus permisos, sin controles de filtro
    clientes_sel = clientes_opts
    centros_sel  = centros_opts
    modo_clientes = "Incluir seleccionados"
    modo_centros  = "Incluir seleccionados"
    with f1:
        _txt_cli = ", ".join(clientes_sel) if clientes_sel else "Todos"
        st.caption(f"**Clientes:** {_txt_cli}")
    with f2:
        _txt_ctr = ", ".join(centros_sel) if centros_sel else "Todos"
        st.caption(f"**Centros:** {_txt_ctr}")
cerrar_bloque_mobile_stack()

if centros_sel and not sin_fact and "linea_negocio" in df_fact_raw.columns and "cliente" in df_fact_raw.columns:
    centros_set_main = set([c.strip() for c in centros_sel])
    mask_rel = df_fact_raw["linea_negocio"].astype(str).str.strip().isin(centros_set_main)
    if modo_centros == "Excluir seleccionados":
        mask_rel = ~mask_rel
    clientes_rel = (
        df_fact_raw.loc[mask_rel, "cliente"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.title()
        .unique()
        .tolist()
    )
    st.caption(f"Impacto CC por relación Facturación↔Cliente: {len(clientes_rel):,} clientes")

estado_ui_actual = {
    "fecha_desde": fecha_desde.isoformat(),
    "fecha_hasta": fecha_hasta.isoformat(),
    "modo_filtro_clientes": modo_clientes,
    "filtro_global_clientes": clientes_sel,
    "modo_filtro_centros": modo_centros,
    "filtro_global_centros": centros_sel,
}
if _es_superusuario and estado_ui_actual != estado_ui_global:
    guardar_estado_ui_global(estado_ui_actual)

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
    incluir_clientes = modo_clientes == "Incluir seleccionados"
    mask_df = df["cliente"].astype(str).str.strip().str.title().isin(clientes_set)
    mask_df_sa = df_sa["cliente"].astype(str).str.strip().str.title().isin(clientes_set)
    mask_df_llc = df_llc["cliente"].astype(str).str.strip().str.title().isin(clientes_set)
    mask_df_ars = df_ars["cliente"].astype(str).str.strip().str.title().isin(clientes_set)
    mask_df_usd = df_usd["cliente"].astype(str).str.strip().str.title().isin(clientes_set)

    df = df[mask_df if incluir_clientes else ~mask_df]
    df_sa = df_sa[mask_df_sa if incluir_clientes else ~mask_df_sa]
    df_llc = df_llc[mask_df_llc if incluir_clientes else ~mask_df_llc]
    df_ars = df_ars[mask_df_ars if incluir_clientes else ~mask_df_ars]
    df_usd = df_usd[mask_df_usd if incluir_clientes else ~mask_df_usd]

if not sin_cc and clientes_sel:
    clientes_set = set([c.strip().title() for c in clientes_sel])
    incluir_clientes = modo_clientes == "Incluir seleccionados"
    mask_cc = df_saldos["Cliente"].astype(str).str.strip().str.title().isin(clientes_set)
    df_saldos = df_saldos[mask_cc if incluir_clientes else ~mask_cc]
    if df_cc_mov is not None and "Cliente" in df_cc_mov.columns:
        mask_mov = df_cc_mov["Cliente"].astype(str).str.strip().str.title().isin(clientes_set)
        df_cc_mov = df_cc_mov[mask_mov if incluir_clientes else ~mask_mov]
    if not sin_comp and "Cliente" in df_cc_comp.columns:
        mask_comp_cli = df_cc_comp["Cliente"].astype(str).str.strip().str.title().isin(clientes_set)
        df_cc_comp = df_cc_comp[mask_comp_cli if incluir_clientes else ~mask_comp_cli]

if centros_sel:
    centros_set = set([c.strip() for c in centros_sel])
    incluir_centros = modo_centros == "Incluir seleccionados"
    if not sin_fact and "linea_negocio" in df.columns:
        mask_df = df["linea_negocio"].astype(str).str.strip().isin(centros_set)
        mask_df_sa = df_sa["linea_negocio"].astype(str).str.strip().isin(centros_set)
        mask_df_llc = df_llc["linea_negocio"].astype(str).str.strip().isin(centros_set)
        mask_df_ars = df_ars["linea_negocio"].astype(str).str.strip().isin(centros_set)
        mask_df_usd = df_usd["linea_negocio"].astype(str).str.strip().isin(centros_set)

        df = df[mask_df if incluir_centros else ~mask_df]
        df_sa = df_sa[mask_df_sa if incluir_centros else ~mask_df_sa]
        df_llc = df_llc[mask_df_llc if incluir_centros else ~mask_df_llc]
        df_ars = df_ars[mask_df_ars if incluir_centros else ~mask_df_ars]
        df_usd = df_usd[mask_df_usd if incluir_centros else ~mask_df_usd]

    # Relacionar centros con clientes via facturacion para que el filtro global
    # impacte tambien en cuentas corrientes aunque CC no tenga centro por fila.
    clientes_centro = set()
    if not sin_fact and "cliente" in df.columns:
        clientes_centro.update(
            df["cliente"].dropna().astype(str).str.strip().str.title().tolist()
        )

    if not sin_comp and "centro_costo" in df_cc_comp.columns:
        mask_comp_centro = df_cc_comp["centro_costo"].astype(str).str.strip().isin(centros_set)
        df_cc_comp = df_cc_comp[mask_comp_centro if incluir_centros else ~mask_comp_centro]
        clientes_centro.update(
            df_cc_comp["Cliente"].dropna().astype(str).str.strip().str.title().tolist()
        )

    if not sin_cc and clientes_centro:
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

    saldo_vencido_comp = (
        pd.to_numeric(df_saldos.get("saldo_vencido_comp", 0), errors="coerce").fillna(0)
        if "saldo_vencido_comp" in df_saldos.columns
        else pd.Series(0, index=df_saldos.index)
    )
    saldo_vencido_base = pd.to_numeric(df_saldos.get("saldo_vencido", 0), errors="coerce").fillna(0)
    df_saldos["saldo_vencido_base"] = saldo_vencido_comp.where(saldo_comp > 0, saldo_vencido_base)

    saldo_por_vencer_comp = (
        pd.to_numeric(df_saldos.get("saldo_por_vencer_comp", 0), errors="coerce").fillna(0)
        if "saldo_por_vencer_comp" in df_saldos.columns
        else pd.Series(0, index=df_saldos.index)
    )
    saldo_por_vencer_base = pd.to_numeric(df_saldos.get("saldo_por_vencer", 0), errors="coerce").fillna(0)
    df_saldos["saldo_por_vencer_base"] = saldo_por_vencer_comp.where(saldo_comp > 0, saldo_por_vencer_base)

    dias_vencido_comp = (
        pd.to_numeric(df_saldos.get("dias_vencido_comp", 0), errors="coerce").fillna(0)
        if "dias_vencido_comp" in df_saldos.columns
        else pd.Series(0, index=df_saldos.index)
    )
    dias_vencido_base = pd.to_numeric(df_saldos.get("dias_vencido", 0), errors="coerce").fillna(0)
    df_saldos["dias_vencido_base"] = dias_vencido_comp.where(saldo_comp > 0, dias_vencido_base).astype(int)

    dias_vencido_max_comp = (
        pd.to_numeric(df_saldos.get("dias_vencido_max_comp", 0), errors="coerce").fillna(0)
        if "dias_vencido_max_comp" in df_saldos.columns
        else pd.Series(0, index=df_saldos.index)
    )
    dias_vencido_max_base = pd.to_numeric(df_saldos.get("dias_vencido_max", 0), errors="coerce").fillna(0)
    df_saldos["dias_vencido_max_base"] = dias_vencido_max_comp.where(saldo_comp > 0, dias_vencido_max_base).astype(int)

    df_saldos["aging_base"] = df_saldos["dias_vencido_base"].apply(calcular_aging)
    df_saldos["fuente_cc_base"] = np.where(saldo_comp > 0, "composicion", "cc_movimientos")

col_deuda_cc = "saldo_deuda" if (not sin_cc and "saldo_deuda" in df_saldos.columns) else "saldo_actual"
col_vencida_cc = "saldo_vencido_base" if (not sin_cc and "saldo_vencido_base" in df_saldos.columns) else "saldo_vencido"
col_por_vencer_cc = "saldo_por_vencer_base" if (not sin_cc and "saldo_por_vencer_base" in df_saldos.columns) else "saldo_por_vencer"
col_dias_cc = "dias_vencido_base" if (not sin_cc and "dias_vencido_base" in df_saldos.columns) else "dias_vencido"
col_dias_max_cc = "dias_vencido_max_base" if (not sin_cc and "dias_vencido_max_base" in df_saldos.columns) else "dias_vencido_max"
col_aging_cc = "aging_base" if (not sin_cc and "aging_base" in df_saldos.columns) else "aging"

# ═══════════════════════════════════════════════════
# NAVEGACIÓN POR SECCIONES (controlada desde sidebar)
# ═══════════════════════════════════════════════════
 
# ══════════════════════════════════════════════
# SECCIÓN 1 — FACTURACIÓN
# ══════════════════════════════════════════════
if st.session_state["tab_nav"] == "Facturación":
    if sin_fact or df.empty:
        st.info("Sin datos. Colocá datos_facturacion.xlsx en data/raw/ y actualizá.")
    else:
        st.markdown("### Facturación Detallada")
        st.caption("Vista analítica por empresa, línea de negocio y clientes.")

        c1, c2, c3 = st.columns(3)
        total_sa_t2  = df_sa["monto_total_ars"].sum()  if not df_sa.empty  else 0
        total_llc_t2 = df_llc["monto_total_ars"].sum() if not df_llc.empty else 0
        total_usd_t2 = df["monto_usd"].sum() if not df.empty else 0
        c1.metric("Total Facturación TIARG S.A.", fmt_m(total_sa_t2))
        c2.metric("Total Facturación TIARG LLC",  fmt_m(total_llc_t2, "USD"))
        c3.metric("Consolidado USD (Imp. usd)", fmt_m(total_usd_t2, "USD"))
 
        st.markdown("---")
        abrir_bloque_mobile_stack()
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
            cerrar_bloque_mobile_stack()
 
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
 
        abrir_bloque_mobile_stack()
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
            cerrar_bloque_mobile_stack()
 
 
# ══════════════════════════════════════════════
# SECCIÓN 2 — CUENTAS CORRIENTES
# ══════════════════════════════════════════════
if st.session_state["tab_nav"] == "CC":
    if sin_cc:
        st.info("Sin datos de CC. Colocá cc_clientes.xlsx en data/raw/ y actualizá.")
    else:
        st.markdown("### Gestión de Cobranzas")

        df_cc_view = df_saldos.copy()
        for c in [col_deuda_cc, col_vencida_cc, col_dias_cc]:
            if c in df_cc_view.columns:
                df_cc_view[c] = pd.to_numeric(df_cc_view[c], errors="coerce").fillna(0)

        # ── Composición de saldos (movimientos Debe/Haber) ───────────────
        st.markdown("#### Composición de saldos")
        if df_cc_mov is None or df_cc_mov.empty:
            st.info("Sin datos de movimientos. Cargá cc_clientes.xlsx y actualizá.")
        else:
            clientes_mov = sorted(
                df_cc_mov["Cliente"].dropna().astype(str).str.strip().str.title().unique().tolist()
            )
            cliente_mov_sel = st.selectbox(
                "Cliente",
                options=[""] + clientes_mov,
                format_func=lambda x: "— elegí un cliente para ver el detalle —" if x == "" else x,
                key="mov_cliente_sel",
            )

            if cliente_mov_sel:
                mov_cli = df_cc_mov[
                    df_cc_mov["Cliente"].astype(str).str.strip().str.title()
                    == cliente_mov_sel.strip().title()
                ].copy()

                # Ordenar por fecha de movimiento
                if "Fecha" in mov_cli.columns:
                    mov_cli["Fecha"] = pd.to_datetime(mov_cli["Fecha"], errors="coerce")
                    mov_cli = mov_cli.sort_values("Fecha")

                # Construir tabla de display
                mov_tabla = pd.DataFrame()
                if "Fecha" in mov_cli.columns:
                    mov_tabla["Fecha"] = mov_cli["Fecha"].dt.strftime("%d/%m/%Y")
                if "Documento" in mov_cli.columns:
                    mov_tabla["Documento"] = mov_cli["Documento"].astype(str)
                if "Descripción" in mov_cli.columns:
                    mov_tabla["Descripción"] = mov_cli["Descripción"].astype(str)
                if "Fecha vencimiento" in mov_cli.columns:
                    mov_tabla["Vencimiento"] = pd.to_datetime(
                        mov_cli["Fecha vencimiento"], errors="coerce"
                    ).dt.strftime("%d/%m/%Y")
                if "tipo" in mov_cli.columns:
                    mov_tabla["Tipo"] = mov_cli["tipo"].astype(str)
                for col_orig, col_dest in [("Debe ppal", "Debe"), ("Haber ppal", "Haber"), ("Saldo ppal", "Saldo")]:
                    if col_orig in mov_cli.columns:
                        vals = pd.to_numeric(mov_cli[col_orig], errors="coerce").fillna(0)
                        mov_tabla[col_dest] = vals.map(
                            lambda v: f"$ {v:,.0f}" if v != 0 else ""
                        )

                # Resumen rápido
                debe_total  = pd.to_numeric(mov_cli.get("Debe ppal",  pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
                haber_total = pd.to_numeric(mov_cli.get("Haber ppal", pd.Series(dtype=float)), errors="coerce").fillna(0).sum()
                saldo_final = pd.to_numeric(mov_cli.get("Saldo ppal", pd.Series(dtype=float)), errors="coerce").fillna(0).iloc[-1] if len(mov_cli) else 0

                m1, m2, m3 = st.columns(3)
                m1.metric("Total facturado (Debe)", f"$ {debe_total:,.0f}")
                m2.metric("Total cobrado (Haber)",  f"$ {haber_total:,.0f}")
                m3.metric("Saldo actual",            f"$ {saldo_final:,.0f}")

                st.dataframe(mov_tabla, use_container_width=True, hide_index=True)
            else:
                # Sin cliente seleccionado: mostrar resumen por cliente
                if "Cliente" in df_cc_mov.columns:
                    debe_col  = "Debe ppal"  if "Debe ppal"  in df_cc_mov.columns else None
                    haber_col = "Haber ppal" if "Haber ppal" in df_cc_mov.columns else None
                    saldo_col = "Saldo ppal" if "Saldo ppal" in df_cc_mov.columns else None

                    agg_dict = {}
                    if debe_col:  agg_dict["Facturado (Debe)"]  = (debe_col,  "sum")
                    if haber_col: agg_dict["Cobrado (Haber)"]   = (haber_col, "sum")

                    if agg_dict:
                        resumen_mov = df_cc_mov.groupby("Cliente", as_index=False).agg(**agg_dict)
                        if debe_col and haber_col:
                            resumen_mov["Saldo neto"] = resumen_mov["Facturado (Debe)"] - resumen_mov["Cobrado (Haber)"]
                        resumen_mov = resumen_mov.sort_values("Facturado (Debe)" if "Facturado (Debe)" in resumen_mov.columns else resumen_mov.columns[-1], ascending=False)
                        for col in ["Facturado (Debe)", "Cobrado (Haber)", "Saldo neto"]:
                            if col in resumen_mov.columns:
                                resumen_mov[col] = resumen_mov[col].map(lambda v: f"$ {v:,.0f}")
                        st.dataframe(resumen_mov, use_container_width=True, hide_index=True)

        st.markdown("---")

        # ── Métricas ──────────────────────────────────────────────────────
        deuda_total   = df_cc_view[col_deuda_cc].sum()
        deuda_vencida = df_cc_view[col_vencida_cc].sum()
        deuda_critica = df_cc_view[df_cc_view[col_aging_cc] == "+90 días"][col_vencida_cc].sum()

        abrir_bloque_mobile_stack()
        c1, c2 = st.columns(2)
        c1.metric("Deuda total",   fmt_m(deuda_total))
        c2.metric("Deuda vencida", fmt_m(deuda_vencida),
                  delta=f"{deuda_critica/deuda_vencida*100:.0f}% en +90" if deuda_vencida else None,
                  delta_color="inverse")
        cerrar_bloque_mobile_stack()

        st.markdown("---")

        # ── Tabla de deudores ─────────────────────────────────────────────
        st.markdown("#### Tabla de deudores")
        top10 = df_cc_view.nlargest(10, col_deuda_cc)[
            ["Cliente", col_deuda_cc, col_vencida_cc, col_dias_cc, col_aging_cc]
        ]
        top10_tabla = top10.rename(columns={
            col_deuda_cc:   "Saldo",
            col_vencida_cc: "Vencido",
            col_dias_cc:    "Días vencido",
            col_aging_cc:   "Estado",
        }).copy()
        top10_tabla["Saldo"]        = pd.to_numeric(top10_tabla["Saldo"],        errors="coerce").fillna(0)
        top10_tabla["Vencido"]      = pd.to_numeric(top10_tabla["Vencido"],      errors="coerce").fillna(0)
        top10_tabla["Días vencido"] = pd.to_numeric(top10_tabla["Días vencido"], errors="coerce").fillna(0).astype(int)
        top10_tabla["Saldo_fmt"]    = top10_tabla["Saldo"].map(lambda v: f"$ {v:,.0f}")
        top10_tabla["Vencido_fmt"]  = top10_tabla["Vencido"].map(lambda v: f"$ {v:,.0f}")

        evento_top10 = st.dataframe(
            top10_tabla[["Cliente", "Saldo_fmt", "Vencido_fmt", "Días vencido", "Estado"]].rename(columns={
                "Saldo_fmt": "Saldo",
                "Vencido_fmt": "Vencido",
            }),
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
        )

        if evento_top10.selection["rows"]:
            idx_sel = evento_top10.selection["rows"][0]
            cliente_sel = top10_tabla.iloc[idx_sel]["Cliente"]

            with st.expander(f"Comprobantes adeudados · {cliente_sel}", expanded=True):
                if not sin_comp and df_cc_comp is not None and not df_cc_comp.empty:
                    comprobantes_cli = df_cc_comp[
                        df_cc_comp["Cliente"].astype(str).str.strip().str.title() == cliente_sel.strip().title()
                    ].copy()
                    comprobantes_cli["saldo_abierto"] = pd.to_numeric(
                        comprobantes_cli.get("saldo_abierto", 0), errors="coerce"
                    ).fillna(0)
                    comprobantes_cli = comprobantes_cli[comprobantes_cli["saldo_abierto"] > 0].copy()

                    if "Documento_ref" in comprobantes_cli.columns:
                        tipo_doc = comprobantes_cli["Documento_ref"].astype(str).str.upper()
                        mask_docs = (
                            tipo_doc.str.contains("FAC", na=False)
                            | tipo_doc.str.contains("FACT", na=False)
                            | tipo_doc.str.contains("ND", na=False)
                            | tipo_doc.str.contains("DEBIT", na=False)
                        )
                        if mask_docs.any():
                            comprobantes_cli = comprobantes_cli[mask_docs].copy()

                    if comprobantes_cli.empty:
                        st.success(f"Sin comprobantes adeudados para {cliente_sel}.")
                    else:
                        comp_tabla = pd.DataFrame()
                        if "Documento_ref" in comprobantes_cli.columns:
                            comp_tabla["Comprobante"] = comprobantes_cli["Documento_ref"].astype(str)
                        else:
                            comp_tabla["Comprobante"] = pd.Series([""] * len(comprobantes_cli), index=comprobantes_cli.index)
                        comp_tabla["Saldo"] = comprobantes_cli["saldo_abierto"].map(lambda v: f"$ {v:,.0f}")
                        if "venc_comp" in comprobantes_cli.columns:
                            comp_tabla["Vencimiento"] = pd.to_datetime(
                                comprobantes_cli["venc_comp"], errors="coerce"
                            ).dt.strftime("%d/%m/%Y")
                        if "dias_vencido_item" in comprobantes_cli.columns:
                            dias = pd.to_numeric(comprobantes_cli["dias_vencido_item"], errors="coerce").fillna(0)
                            comp_tabla["Prioridad"] = np.where(
                                dias > 90, "Alta",
                                np.where(dias > 30, "Media", "Baja"),
                            )
                        st.dataframe(comp_tabla, use_container_width=True, hide_index=True)
                else:
                    st.info("Sin datos de composición para mostrar comprobantes adeudados.")

        st.markdown("---")

        # ── Gráficos ──────────────────────────────────────────────────────
        abrir_bloque_mobile_stack()
        col_a, col_b = st.columns(2)

        with col_a:
            st.markdown("#### Aging de deuda")
            aging_df = (df_cc_view.groupby(col_aging_cc)[col_deuda_cc]
                        .sum().reindex(AGING_ORDEN).dropna().reset_index())
            fig6 = px.bar(aging_df, x=col_aging_cc, y=col_deuda_cc,
                          color=col_aging_cc, color_discrete_map=AGING_COLOR,
                          labels={col_aging_cc: "", col_deuda_cc: "ARS"}, text_auto=".2s")
            fig6.update_layout(showlegend=False, margin=dict(t=5, b=5))
            st.plotly_chart(fig6, use_container_width=True)

        with col_b:
            st.markdown("#### Top 10 deudores")
            fig7 = px.bar(top10.sort_values(col_deuda_cc), x=col_deuda_cc, y="Cliente",
                          orientation="h", color=col_aging_cc, color_discrete_map=AGING_COLOR,
                          labels={col_deuda_cc: "ARS", "Cliente": ""}, text_auto=".2s")
            fig7.update_layout(showlegend=True, margin=dict(t=5, b=5, l=10))
            st.plotly_chart(fig7, use_container_width=True)
        cerrar_bloque_mobile_stack()

        csv_cc = df_saldos.to_csv(index=False).encode("utf-8")
        st.download_button("Exportar CC", csv_cc, "cc_saldos.csv", "text/csv")
 
 
# ══════════════════════════════════════════════
# SECCIÓN 3 — CLIENTES (cruce facturación + CC)
# ══════════════════════════════════════════════
if st.session_state["tab_nav"] == "Clientes":
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
                df_saldos[["Cliente", col_deuda_cc, col_vencida_cc, col_aging_cc, col_dias_cc, "ratio_cobranza"]]
                .rename(columns={
                    col_deuda_cc: "saldo_actual",
                    col_vencida_cc: "saldo_vencido",
                    col_aging_cc: "aging",
                    col_dias_cc: "dias_vencido",
                }),
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
 
        # Tabla resumen
        st.markdown("#### Tabla resumen")
        cols_tabla = ["Cliente","Facturado ARS","Deuda ARS","saldo_vencido","ratio_cobranza","aging","dias_vencido"]
        cols_tabla = [c for c in cols_tabla if c in cruce.columns]
        cruce_tabla = cruce[cols_tabla].rename(columns={
            "saldo_vencido":"Saldo vencido","ratio_cobranza":"% Cobrado",
            "aging":"Estado","dias_vencido":"Días vencido"
        }).copy()
        for col_num in ["Facturado ARS", "Deuda ARS", "Saldo vencido", "% Cobrado", "Días vencido"]:
            if col_num in cruce_tabla.columns:
                cruce_tabla[col_num] = pd.to_numeric(cruce_tabla[col_num], errors="coerce").fillna(0)
        if "Facturado ARS" in cruce_tabla.columns:
            cruce_tabla["Facturado ARS"] = cruce_tabla["Facturado ARS"].map(lambda v: f"$ {v:,.0f}")
        if "Deuda ARS" in cruce_tabla.columns:
            cruce_tabla["Deuda ARS"] = cruce_tabla["Deuda ARS"].map(lambda v: f"$ {v:,.0f}")
        if "Saldo vencido" in cruce_tabla.columns:
            cruce_tabla["Saldo vencido"] = cruce_tabla["Saldo vencido"].map(lambda v: f"$ {v:,.0f}")
        if "% Cobrado" in cruce_tabla.columns:
            cruce_tabla["% Cobrado"] = cruce_tabla["% Cobrado"].map(lambda v: f"{v:.0f}%")
        if "Días vencido" in cruce_tabla.columns:
            cruce_tabla["Días vencido"] = cruce_tabla["Días vencido"].map(lambda v: f"{int(v)}")

        st.dataframe(
            cruce_tabla,
            use_container_width=True,
            hide_index=True,
        )

# ══════════════════════════════════════════════
# SECCIÓN ADMIN — solo superusuarios
# ══════════════════════════════════════════════
if st.session_state.get("tab_nav") == "Admin" and _es_superusuario:

    st.markdown("""
    <style>
    .admin-header {
        font-family: 'Sora', 'Segoe UI', Arial, sans-serif;
        font-size: 1.55rem;
        font-weight: 800;
        color: #0f172a;
        letter-spacing: -0.03em;
        margin-bottom: 0.15rem;
    }
    .admin-sub {
        font-size: 0.85rem;
        color: #64748b;
        margin-bottom: 2rem;
    }
    .admin-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 1.4rem 1.6rem 1.2rem 1.6rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 4px 16px rgba(15,23,42,0.05);
    }
    .admin-card-title {
        font-size: 1rem;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 0.8rem;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }
    .admin-badge {
        display: inline-block;
        background: #f1f5f9;
        color: #475569;
        font-size: 0.72rem;
        font-weight: 600;
        padding: 2px 8px;
        border-radius: 99px;
        margin-left: 6px;
        letter-spacing: 0.02em;
        vertical-align: middle;
    }
    .admin-divider {
        border: none;
        border-top: 1px solid #f1f5f9;
        margin: 1rem 0;
    }
    .admin-label {
        font-size: 0.78rem;
        font-weight: 600;
        color: #475569;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.3rem;
    }
    .admin-hint {
        font-size: 0.75rem;
        color: #94a3b8;
        margin-top: 0.2rem;
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="admin-header">⚙ Gestión de usuarios</div>', unsafe_allow_html=True)
    st.markdown('<div class="admin-sub">Configurá accesos y permisos de cada usuario. Solo los superusuarios pueden ver esta sección.</div>', unsafe_allow_html=True)

    _perms_edit = _cargar_permisos()
    _users_edit = dict(_perms_edit.get("users", {}))

    # ── Card: Superusuarios ─────────────────────────
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.markdown('<div class="admin-card-title">👑 Superusuarios</div>', unsafe_allow_html=True)
    st.markdown('<div class="admin-label">Usuarios con acceso total (separados por coma)</div>', unsafe_allow_html=True)
    _supers_str = st.text_input(
        "superusuarios",
        value=", ".join(_perms_edit.get("superusers", [])),
        key="admin_supers",
        label_visibility="collapsed",
        placeholder="ej: admin, sebastian",
    )
    st.markdown('<div class="admin-hint">Estos usuarios ven todo y pueden gestionar permisos.</div>', unsafe_allow_html=True)
    if st.button("Guardar superusuarios", key="admin_save_supers", type="primary"):
        _perms_edit["superusers"] = [s.strip() for s in _supers_str.split(",") if s.strip()]
        if _guardar_permisos(_perms_edit):
            st.success("✓ Superusuarios guardados.")
        else:
            st.error("No se pudo guardar. Revisá permisos del archivo.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Card: Generador de contraseña ───────────────
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.markdown('<div class="admin-card-title">🔑 Generar contraseña para un usuario</div>', unsafe_allow_html=True)
    st.markdown('<div class="admin-hint" style="margin-bottom:0.8rem;">Generá el hash de la contraseña y pegalo en la variable <b>AUTH_USERS</b> de Railway.</div>', unsafe_allow_html=True)
    _gcol1, _gcol2, _gcol3 = st.columns([2, 2, 1])
    with _gcol1:
        _gen_user = st.text_input("Usuario", key="gen_user", placeholder="nombre de usuario", label_visibility="collapsed")
    with _gcol2:
        _gen_pass = st.text_input("Contraseña", key="gen_pass", placeholder="contraseña", type="password", label_visibility="collapsed")
    with _gcol3:
        _gen_btn = st.button("Generar", key="gen_btn", use_container_width=True, type="primary")

    if _gen_btn:
        if _gen_user.strip() and _gen_pass:
            _gen_salt, _ = _get_auth_config()
            if _gen_salt:
                _gen_hash = _hash_password(_gen_pass, _gen_salt)
                _gen_entry = f"{_gen_user.strip()}:{_gen_hash}"
                st.success("✓ Hash generado. Copiá la línea de abajo y pegala en Railway → Variables → AUTH_USERS (separando usuarios con coma).")
                st.code(_gen_entry, language=None)
            else:
                st.error("No se encontró AUTH_SALT. Configurá la variable en Railway primero.")
        else:
            st.warning("Completá usuario y contraseña.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Card: Agregar nuevo usuario ─────────────────
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.markdown('<div class="admin-card-title">➕ Agregar usuario regular</div>', unsafe_allow_html=True)
    _col_new1, _col_new2 = st.columns([3, 1])
    with _col_new1:
        _nuevo = st.text_input(
            "nombre usuario",
            key="admin_nuevo_user",
            label_visibility="collapsed",
            placeholder="nombre de usuario exacto (igual al login)",
        ).strip()
    with _col_new2:
        if st.button("Agregar", key="admin_add_user", use_container_width=True, type="primary"):
            if _nuevo and _nuevo not in _users_edit:
                _users_edit[_nuevo] = {"clientes": [], "centros": [], "tabs": []}
                _perms_edit["users"] = _users_edit
                _perms_edit["superusers"] = [s.strip() for s in _supers_str.split(",") if s.strip()]
                _guardar_permisos(_perms_edit)
                st.success(f"✓ Usuario '{_nuevo}' agregado.")
                st.rerun()
            elif _nuevo in _users_edit:
                st.warning("Ese usuario ya existe.")
            else:
                st.warning("Ingresá un nombre de usuario.")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Cards por usuario ───────────────────────────
    if _users_edit:
        st.markdown(f"### Usuarios regulares <span class='admin-badge'>{len(_users_edit)}</span>", unsafe_allow_html=True)
        for _uname, _uprefs in list(_users_edit.items()):
            st.markdown(f'<div class="admin-card">', unsafe_allow_html=True)
            _hcol1, _hcol2 = st.columns([4, 1])
            with _hcol1:
                st.markdown(f'<div class="admin-card-title">👤 {_uname}</div>', unsafe_allow_html=True)
            with _hcol2:
                if st.button("🗑 Eliminar", key=f"admin_del_{_uname}", use_container_width=True):
                    _users_edit.pop(_uname, None)
                    _perms_edit["users"] = _users_edit
                    _perms_edit["superusers"] = [s.strip() for s in _supers_str.split(",") if s.strip()]
                    _guardar_permisos(_perms_edit)
                    st.rerun()

            # ── Clientes ──
            st.markdown('<div class="admin-label">Clientes</div>', unsafe_allow_html=True)
            _cli_modo_actual = _uprefs.get("clientes_modo", "Excluir")
            _ccol1, _ccol2 = st.columns([1, 3])
            with _ccol1:
                _cli_modo = st.radio(
                    f"modo_cli_{_uname}",
                    ["Excluir", "Incluir"],
                    index=0 if _cli_modo_actual == "Excluir" else 1,
                    key=f"admin_cli_modo_{_uname}",
                    label_visibility="collapsed",
                    help="Excluir: el usuario ve todos menos los seleccionados.\nIncluir: el usuario ve solo los seleccionados.",
                )
            with _ccol2:
                _cli_label = "Clientes a excluir" if _cli_modo == "Excluir" else "Clientes a incluir"
                _cli_val = st.multiselect(
                    _cli_label,
                    options=clientes_opts,
                    default=[c for c in _uprefs.get("clientes", []) if c in clientes_opts],
                    key=f"admin_cli_{_uname}",
                    label_visibility="collapsed",
                    placeholder=f"Seleccioná clientes a {_cli_modo.lower()}...",
                )
            _n_cli = len(_cli_val)
            _total_cli = len(clientes_opts)
            _resultado_cli = _total_cli - _n_cli if _cli_modo == "Excluir" else _n_cli
            st.markdown(
                f'<div class="admin-hint">El usuario verá <b>{_resultado_cli}</b> de {_total_cli} clientes.</div>',
                unsafe_allow_html=True,
            )

            st.markdown('<hr class="admin-divider">', unsafe_allow_html=True)

            # ── Centros de costo ──
            st.markdown('<div class="admin-label">Centros de costo</div>', unsafe_allow_html=True)
            _ctr_modo_actual = _uprefs.get("centros_modo", "Excluir")
            _ctrcol1, _ctrcol2 = st.columns([1, 3])
            with _ctrcol1:
                _ctr_modo = st.radio(
                    f"modo_ctr_{_uname}",
                    ["Excluir", "Incluir"],
                    index=0 if _ctr_modo_actual == "Excluir" else 1,
                    key=f"admin_ctr_modo_{_uname}",
                    label_visibility="collapsed",
                    help="Excluir: el usuario ve todos menos los seleccionados.\nIncluir: el usuario ve solo los seleccionados.",
                )
            with _ctrcol2:
                _ctr_label = "Centros a excluir" if _ctr_modo == "Excluir" else "Centros a incluir"
                _ctr_val = st.multiselect(
                    _ctr_label,
                    options=centros_opts,
                    default=[c for c in _uprefs.get("centros", []) if c in centros_opts],
                    key=f"admin_ctr_{_uname}",
                    label_visibility="collapsed",
                    placeholder=f"Seleccioná centros a {_ctr_modo.lower()}...",
                )
            _n_ctr = len(_ctr_val)
            _total_ctr = len(centros_opts)
            _resultado_ctr = _total_ctr - _n_ctr if _ctr_modo == "Excluir" else _n_ctr
            st.markdown(
                f'<div class="admin-hint">El usuario verá <b>{_resultado_ctr}</b> de {_total_ctr} centros.</div>',
                unsafe_allow_html=True,
            )

            st.markdown('<hr class="admin-divider">', unsafe_allow_html=True)

            # ── Pestañas ──
            st.markdown('<div class="admin-label">Pestañas habilitadas</div>', unsafe_allow_html=True)
            _tabs_disponibles = ["Facturación", "CC", "Clientes"]
            _tabs_actuales = _uprefs.get("tabs", [])
            _tabs_val = st.multiselect(
                f"tabs_{_uname}",
                options=_tabs_disponibles,
                default=[t for t in _tabs_actuales if t in _tabs_disponibles],
                key=f"admin_tabs_{_uname}",
                label_visibility="collapsed",
                placeholder="Todas (sin restricción)",
            )
            st.markdown(
                '<div class="admin-hint">Dejá vacío para habilitar todas las pestañas.</div>',
                unsafe_allow_html=True,
            )

            if st.button("💾 Guardar cambios", key=f"admin_save_{_uname}", type="primary"):
                _users_edit[_uname] = {
                    "clientes":      _cli_val,
                    "clientes_modo": _cli_modo,
                    "centros":       _ctr_val,
                    "centros_modo":  _ctr_modo,
                    "tabs":          _tabs_val,
                }
                _perms_edit["users"] = _users_edit
                _perms_edit["superusers"] = [s.strip() for s in _supers_str.split(",") if s.strip()]
                if _guardar_permisos(_perms_edit):
                    st.success(f"✓ Permisos de '{_uname}' guardados.")
                else:
                    st.error("No se pudo guardar. Revisá permisos del archivo.")
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No hay usuarios regulares todavía. Agregá uno arriba.")
