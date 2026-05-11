"""
Capa de persistencia — Finnegans BI
------------------------------------
Si DATABASE_URL está configurada  →  PostgreSQL (Railway)
Si no                             →  archivos parquet/json locales

Uso:
    from etl.db import guardar, cargar, guardar_permisos, cargar_permisos, tiene_db
"""

from __future__ import annotations
import os
import json
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path("data/processed")
_PERMISOS_LOCAL = Path(__file__).parent.parent / "dashboard" / "permisos.json"

# ── Conexión ────────────────────────────────────────────────────────────────

def _get_engine():
    """Devuelve un engine SQLAlchemy si DATABASE_URL está disponible, sino None."""
    url = os.getenv("DATABASE_URL", "")
    if not url:
        return None
    try:
        from sqlalchemy import create_engine
        # Railway usa postgres://, SQLAlchemy 2.x requiere postgresql://
        url = url.replace("postgres://", "postgresql://", 1)
        return create_engine(url, pool_pre_ping=True)
    except Exception as e:
        print(f"  ⚠ No se pudo conectar a la base de datos: {e}")
        return None


def tiene_db() -> bool:
    """True si hay DATABASE_URL configurada."""
    return bool(os.getenv("DATABASE_URL", ""))


# ── Guardar ─────────────────────────────────────────────────────────────────

def guardar(df: pd.DataFrame, nombre: str) -> None:
    """
    Guarda un DataFrame.
    - En Railway (DATABASE_URL): tabla PostgreSQL, reemplaza todo.
    - Local: parquet en data/processed/.
    """
    engine = _get_engine()
    if engine is not None:
        # Convertir columnas datetime con timezone a naive para PostgreSQL
        for col in df.select_dtypes(include=["datetimetz"]).columns:
            df[col] = df[col].dt.tz_localize(None)
        try:
            with engine.begin() as conn:
                df.to_sql(nombre, conn, if_exists="replace", index=False)
            print(f"  ✓ {nombre} → PostgreSQL ({len(df)} filas)")
            return
        except Exception as e:
            print(f"  ⚠ Error guardando en DB, fallback a parquet: {e}")

    # Fallback local
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.to_parquet(PROCESSED_DIR / f"{nombre}.parquet", index=False)
    print(f"  ✓ {nombre}.parquet ({len(df)} filas)")


# ── Cargar ──────────────────────────────────────────────────────────────────

def cargar(nombre: str) -> pd.DataFrame | None:
    """
    Carga un DataFrame.
    - En Railway (DATABASE_URL): desde tabla PostgreSQL.
    - Local: desde parquet/csv en data/processed/.
    Devuelve None si no existe.
    """
    engine = _get_engine()
    if engine is not None:
        try:
            from sqlalchemy import text, inspect
            insp = inspect(engine)
            if nombre not in insp.get_table_names():
                return None
            with engine.connect() as conn:
                df = pd.read_sql(text(f'SELECT * FROM "{nombre}"'), conn)
            return df
        except Exception as e:
            print(f"  ⚠ Error leyendo {nombre} de DB, fallback a local: {e}")

    # Fallback local
    for ext in ("parquet", "csv"):
        p = PROCESSED_DIR / f"{nombre}.{ext}"
        if p.exists():
            return pd.read_parquet(p) if ext == "parquet" else pd.read_csv(p, parse_dates=True)
    return None


# ── Meta ────────────────────────────────────────────────────────────────────

def guardar_meta(meta: dict) -> None:
    """Guarda metadata (fecha de actualización, etc.)."""
    engine = _get_engine()
    if engine is not None:
        try:
            df_meta = pd.DataFrame([{"clave": k, "valor": str(v)} for k, v in meta.items()])
            with engine.begin() as conn:
                df_meta.to_sql("meta", conn, if_exists="replace", index=False)
            return
        except Exception as e:
            print(f"  ⚠ Error guardando meta en DB: {e}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROCESSED_DIR / "meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f)


def cargar_meta() -> dict:
    """Carga metadata."""
    engine = _get_engine()
    if engine is not None:
        try:
            from sqlalchemy import text, inspect
            insp = inspect(engine)
            if "meta" not in insp.get_table_names():
                return {}
            with engine.connect() as conn:
                df_meta = pd.read_sql(text('SELECT * FROM "meta"'), conn)
            return dict(zip(df_meta["clave"], df_meta["valor"]))
        except Exception:
            pass

    path = PROCESSED_DIR / "meta.json"
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


# ── Permisos ────────────────────────────────────────────────────────────────

def cargar_permisos() -> dict:
    """
    Carga permisos de usuarios.
    Prioridad: DB → archivo local → env var PERMISSIONS_JSON.
    """
    engine = _get_engine()
    if engine is not None:
        try:
            from sqlalchemy import text, inspect
            insp = inspect(engine)
            if "permisos" in insp.get_table_names():
                with engine.connect() as conn:
                    df_p = pd.read_sql(text('SELECT valor FROM "permisos" WHERE clave = \'datos\''), conn)
                if not df_p.empty:
                    data = json.loads(df_p.iloc[0]["valor"])
                    if isinstance(data, dict):
                        return data
        except Exception as e:
            print(f"  ⚠ Error cargando permisos de DB: {e}")

    # Archivo local
    if _PERMISOS_LOCAL.exists():
        try:
            with open(_PERMISOS_LOCAL, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    # Variable de entorno
    raw = os.getenv("PERMISSIONS_JSON", "")
    if raw:
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    return {"superusers": [], "users": {}}


def guardar_permisos(perms: dict) -> bool:
    """
    Guarda permisos.
    - En Railway: tabla PostgreSQL (persiste entre deploys).
    - Local: archivo JSON.
    """
    engine = _get_engine()
    if engine is not None:
        try:
            df_p = pd.DataFrame([{"clave": "datos", "valor": json.dumps(perms, ensure_ascii=False)}])
            with engine.begin() as conn:
                df_p.to_sql("permisos", conn, if_exists="replace", index=False)
            # También actualizar el archivo local como backup
            try:
                with open(_PERMISOS_LOCAL, "w", encoding="utf-8") as f:
                    json.dump(perms, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"  ⚠ Error guardando permisos en DB: {e}")
            return False

    # Fallback local
    try:
        with open(_PERMISOS_LOCAL, "w", encoding="utf-8") as f:
            json.dump(perms, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
