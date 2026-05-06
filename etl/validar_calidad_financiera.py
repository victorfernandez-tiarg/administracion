"""
Validaciones de calidad financiera para datos procesados.

Uso:
    python etl/validar_calidad_financiera.py
"""

from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path("data/processed")


def load(nombre: str) -> pd.DataFrame | None:
    for ext in ("parquet", "csv"):
        path = PROCESSED_DIR / f"{nombre}.{ext}"
        if path.exists():
            return pd.read_parquet(path) if ext == "parquet" else pd.read_csv(path)
    return None


def check(condition: bool, ok_msg: str, fail_msg: str) -> bool:
    if condition:
        print(f"  OK  {ok_msg}")
        return True
    print(f"  ERR {fail_msg}")
    return False


def main() -> int:
    print("Validando calidad financiera...")
    fact = load("facturas")
    cc = load("cc_saldos")
    comp = load("cc_composicion")

    estado = True

    estado &= check(fact is not None and not fact.empty, "Facturación cargada", "Facturación faltante")
    estado &= check(cc is not None and not cc.empty, "CC saldos cargada", "CC saldos faltante")

    if fact is not None and not fact.empty:
        estado &= check("fecha" in fact.columns, "Columna fecha presente", "Falta columna fecha")
        estado &= check("monto_total_ars" in fact.columns, "Columna monto_total_ars presente", "Falta monto_total_ars")
        if "monto_total_ars" in fact.columns:
            total_fact = pd.to_numeric(fact["monto_total_ars"], errors="coerce").fillna(0).sum()
            estado &= check(total_fact > 0, "Facturación total positiva", "Facturación total no positiva")

    if cc is not None and not cc.empty:
        esperadas = ["Cliente", "saldo_actual", "saldo_vencido", "dias_vencido", "aging"]
        for col in esperadas:
            estado &= check(col in cc.columns, f"Columna {col} presente", f"Falta columna {col}")

        if {"saldo_actual", "saldo_vencido"}.issubset(set(cc.columns)):
            saldo_actual = pd.to_numeric(cc["saldo_actual"], errors="coerce").fillna(0)
            saldo_vencido = pd.to_numeric(cc["saldo_vencido"], errors="coerce").fillna(0)
            estado &= check(
                bool((saldo_vencido <= saldo_actual + 1e-6).all()),
                "saldo_vencido <= saldo_actual",
                "Hay clientes con saldo_vencido mayor al saldo_actual",
            )

        if "dias_vencido" in cc.columns:
            dias = pd.to_numeric(cc["dias_vencido"], errors="coerce").fillna(0)
            estado &= check(bool((dias >= 0).all()), "dias_vencido no negativos", "Hay dias_vencido negativos")

    if comp is None or comp.empty:
        print("  WARN Sin composición de saldos procesada (cc_composicion).")
    else:
        estado &= check("centro_costo" in comp.columns, "Composición con centro_costo", "Composición sin centro_costo")
        estado &= check("saldo_abierto" in comp.columns, "Composición con saldo_abierto", "Composición sin saldo_abierto")
        if "saldo_abierto" in comp.columns:
            saldo_comp = pd.to_numeric(comp["saldo_abierto"], errors="coerce").fillna(0).sum()
            estado &= check(saldo_comp > 0, "Composición con deuda positiva", "Composición sin deuda positiva")

    print("Resultado:", "OK" if estado else "ERROR")
    return 0 if estado else 1


if __name__ == "__main__":
    raise SystemExit(main())
