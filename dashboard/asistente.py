"""
Asistente IA — Finnegans BI
Usa Ollama local para responder preguntas sobre los datos del dashboard.
Los datos nunca salen de la red interna.
"""

import requests
import pandas as pd
from datetime import date

OLLAMA_URL = "http://localhost:11434/api/chat"
MODELO     = "llama3"   # cambiar a "mistral" o "gemma2" si preferís


def generar_contexto(facturas_df: pd.DataFrame | None,
                     cc_df: pd.DataFrame | None,
                     empresa: str,
                     moneda: str) -> str:
    """Genera un resumen compacto de los datos actuales para mandar como contexto al modelo."""

    lineas = [
        f"Hoy es {date.today().strftime('%d/%m/%Y')}.",
        f"Filtro activo: empresa={empresa}, moneda={moneda}.",
        "",
    ]

    # ── Facturación ──────────────────────────────
    if facturas_df is not None and not facturas_df.empty:
        fact = facturas_df[~facturas_df["anulada"]] if "anulada" in facturas_df.columns else facturas_df
        total        = fact["monto_total"].sum()
        total_neto   = fact["monto_neto"].sum() if "monto_neto" in fact.columns else 0
        cant_fact    = len(fact)
        cant_clientes = fact["cliente"].nunique()

        top5 = (
            fact.groupby("cliente")["monto_total"]
            .sum()
            .nlargest(5)
            .round(2)
            .to_dict()
        )

        evol = (
            fact.groupby(["año", "mes"])["monto_total"]
            .sum()
            .round(2)
            .reset_index()
            .tail(12)
            .to_dict("records")
        ) if "año" in fact.columns else []

        lineas += [
            "=== FACTURACIÓN ===",
            f"Total facturado: {total:,.2f} {moneda}",
            f"Total neto: {total_neto:,.2f} {moneda}",
            f"Cantidad de facturas: {cant_fact}",
            f"Clientes activos: {cant_clientes}",
            f"Top 5 clientes por monto: {top5}",
            f"Evolución mensual (últimos 12 meses): {evol}",
            "",
        ]
    else:
        lineas.append("Sin datos de facturación para el período seleccionado.\n")

    # ── Cuentas corrientes ───────────────────────
    if cc_df is not None and not cc_df.empty:
        total_deuda   = cc_df["monto"].sum()
        al_dia        = cc_df[cc_df["aging"] == "Al día"]["monto"].sum() if "aging" in cc_df.columns else 0
        vencido_total = total_deuda - al_dia
        criticos      = cc_df[cc_df["dias_vencido"] > 60] if "dias_vencido" in cc_df.columns else pd.DataFrame()

        aging_resumen = (
            cc_df.groupby("aging")["monto"].sum().round(2).to_dict()
            if "aging" in cc_df.columns else {}
        )

        top5_deuda = (
            cc_df.groupby("cliente")["monto"]
            .sum()
            .nlargest(5)
            .round(2)
            .to_dict()
        )

        clientes_criticos = (
            criticos.groupby("cliente")["monto"]
            .sum()
            .nlargest(10)
            .round(2)
            .to_dict()
            if not criticos.empty else {}
        )

        lineas += [
            "=== CUENTAS CORRIENTES ===",
            f"Deuda total: {total_deuda:,.2f} {moneda}",
            f"Monto al día: {al_dia:,.2f} {moneda}",
            f"Monto vencido: {vencido_total:,.2f} {moneda}",
            f"Distribución por aging: {aging_resumen}",
            f"Top 5 deudores: {top5_deuda}",
            f"Clientes críticos (+60 días vencido): {clientes_criticos}",
            "",
        ]
    else:
        lineas.append("Sin datos de cuentas corrientes.\n")

    return "\n".join(lineas)


def consultar_ollama(historial: list[dict], contexto: str) -> str:
    """
    Manda el historial de chat + contexto a Ollama y devuelve la respuesta.
    historial: lista de {"role": "user"|"assistant", "content": "..."}
    """
    sistema = f"""Sos un asistente financiero experto analizando datos de facturación
y cuentas corrientes de una empresa de software.
Respondés en español, de forma clara y concisa.
Cuando menciones montos, usá puntos como separadores de miles.
Si te preguntan algo que no está en los datos, decilo claramente.
No inventes números.

CONTEXTO ACTUAL DE LOS DATOS:
{contexto}"""

    mensajes = [{"role": "system", "content": sistema}] + historial

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODELO,
                "messages": mensajes,
                "stream": False,
                "options": {"temperature": 0.2},  # bajo para respuestas más precisas
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]

    except requests.exceptions.ConnectionError:
        return (
            "⚠️ No se puede conectar con Ollama. "
            "Asegurate de que esté corriendo con `ollama serve`."
        )
    except requests.exceptions.Timeout:
        return "⚠️ El modelo tardó demasiado en responder. Intentá de nuevo."
    except Exception as e:
        return f"⚠️ Error inesperado: {e}"


def ollama_disponible() -> bool:
    """Chequea si Ollama está corriendo."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def modelos_disponibles() -> list[str]:
    """Lista los modelos instalados en Ollama."""
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        data = r.json()
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []
