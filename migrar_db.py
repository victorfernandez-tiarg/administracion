"""
Migración de base de datos PostgreSQL entre cuentas de Railway
=============================================================
Copia todas las tablas de la DB vieja (tu Railway) a la DB nueva (Railway del jefe).

USO:
    1. Completá las dos URLs abajo (ORIGIN_DATABASE_URL y TARGET_DATABASE_URL)
    2. Ejecutá:  python migrar_db.py

Las URLs las encontrás en cada Railway → proyecto → servicio PostgreSQL → Variables → DATABASE_URL
Formato:  postgresql://user:password@host:port/dbname
"""

import os
import sys

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
# Podés pegarlas directamente aquí, o pasarlas como variables de entorno.

ORIGIN_DATABASE_URL = os.getenv(
    "ORIGIN_DATABASE_URL",
    ""   # ← pegá acá la DATABASE_URL de TU Railway (el viejo)
)

TARGET_DATABASE_URL = os.getenv(
    "TARGET_DATABASE_URL",
    ""   # ← pegá acá la DATABASE_URL del Railway del JEFE (el nuevo)
)

# ──────────────────────────────────────────────────────────────────────────────


def normalizar_url(url: str) -> str:
    """Railway usa postgres://, SQLAlchemy 2.x requiere postgresql://"""
    return url.replace("postgres://", "postgresql://", 1)


def migrar():
    if not ORIGIN_DATABASE_URL:
        print("❌  Falta ORIGIN_DATABASE_URL (DB vieja en tu Railway)")
        sys.exit(1)
    if not TARGET_DATABASE_URL:
        print("❌  Falta TARGET_DATABASE_URL (DB nueva en Railway del jefe)")
        sys.exit(1)

    try:
        from sqlalchemy import create_engine, inspect, text
        import pandas as pd
    except ImportError:
        print("❌  Faltan dependencias. Ejecutá:  pip install sqlalchemy pandas psycopg2-binary")
        sys.exit(1)

    origin_url = normalizar_url(ORIGIN_DATABASE_URL)
    target_url = normalizar_url(TARGET_DATABASE_URL)

    print("🔌  Conectando a la base de datos de origen (vieja)...")
    try:
        engine_origin = create_engine(origin_url, pool_pre_ping=True)
        with engine_origin.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("   ✓ Conexión origen OK")
    except Exception as e:
        print(f"❌  No se pudo conectar al origen: {e}")
        sys.exit(1)

    print("🔌  Conectando a la base de datos de destino (nueva)...")
    try:
        engine_target = create_engine(target_url, pool_pre_ping=True)
        with engine_target.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("   ✓ Conexión destino OK")
    except Exception as e:
        print(f"❌  No se pudo conectar al destino: {e}")
        sys.exit(1)

    # Listar tablas del origen
    inspector = inspect(engine_origin)
    tablas = inspector.get_table_names(schema="public")

    if not tablas:
        print("⚠️  No hay tablas en la base de datos de origen. Nada que migrar.")
        return

    print(f"\n📋  Tablas encontradas ({len(tablas)}): {', '.join(tablas)}\n")

    errores = []
    for tabla in tablas:
        print(f"  → Migrando tabla: {tabla}")
        try:
            df = pd.read_sql_table(tabla, engine_origin, schema="public")

            # Convertir columnas datetime con timezone a naive (evita error en PostgreSQL)
            for col in df.select_dtypes(include=["datetimetz"]).columns:
                df[col] = df[col].dt.tz_localize(None)

            with engine_target.begin() as conn:
                df.to_sql(tabla, conn, if_exists="replace", index=False, schema="public")

            print(f"     ✓ {tabla}: {len(df)} filas copiadas")
        except Exception as e:
            print(f"     ❌ Error en {tabla}: {e}")
            errores.append((tabla, str(e)))

    # Migrar tabla de permisos si existe (tabla especial de la app)
    print("\n  → Verificando tabla 'permisos'...")
    if "permisos" not in tablas:
        print("     ℹ️  No existe tabla 'permisos' en la DB (se usa el archivo local permisos.json)")

    print("\n" + "="*60)
    if errores:
        print(f"⚠️  Migración completada con {len(errores)} errores:")
        for tabla, err in errores:
            print(f"   - {tabla}: {err}")
    else:
        print("✅  Migración completada sin errores.")

    print("\n📌  PRÓXIMO PASO:")
    print("   Actualizá la variable DATABASE_URL en el proyecto del jefe en Railway")
    print("   con el valor de TARGET_DATABASE_URL que usaste en este script.")
    print("   El proyecto se va a redesplegar automáticamente.\n")


if __name__ == "__main__":
    migrar()
