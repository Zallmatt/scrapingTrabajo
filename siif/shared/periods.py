"""Periodos de extracción SIIF: desde 2025 hasta el mes actual."""
from datetime import datetime

START_YEAR = 2025
SKIP_ENTITY_PREFIXES = ("0 ADMINISTRACION",)


def skip_empty_entities(entities):
    """Omite entidades agregadas que SIIF responde sin datos."""
    kept = []
    skipped = []
    for entity in entities:
        name = (entity or "").strip()
        if any(name.startswith(prefix) for prefix in SKIP_ENTITY_PREFIXES):
            skipped.append(name)
        else:
            kept.append(entity)
    if skipped:
        print(f"Entidades omitidas (sin datos): {skipped}")
    return kept


def build_periods(month_mode="single"):
    """
    Devuelve periodos desde enero 2025 hasta el mes actual.

    month_mode:
      - "single": mes a mes (mes_desde = mes_hasta). Recomendado por red.
      - "range": un rango anual (01 hasta mes actual o 12).
    """
    today = datetime.now()
    periods = []

    for year in range(START_YEAR, today.year + 1):
        if year == today.year:
            last_month = today.month
        else:
            last_month = 12

        if month_mode == "range":
            periods.append(
                {
                    "year": str(year),
                    "desde": "01",
                    "hasta": f"{last_month:02d}",
                }
            )
        else:
            periods.append(
                {
                    "year": str(year),
                    "months": [f"{m:02d}" for m in range(1, last_month + 1)],
                }
            )

    return periods
