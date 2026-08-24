"""Límites para pruebas acotadas de extracción SIIF."""
import os

from dotenv import load_dotenv

from shared.periods import START_YEAR


def is_test_mode():
    load_dotenv()
    return os.getenv("SIIF_TEST_MODE", "").lower() in ("1", "true", "yes")


def apply_test_limits(entities, periods=None):
    """
    Filtra entidades y periodos cuando SIIF_TEST_MODE está activo.

    Variables opcionales:
      SIIF_TEST_YEAR (default: START_YEAR)
      SIIF_TEST_MONTH (default: 01)
      SIIF_TEST_MAX_ENTITIES (default: 1)
      SIIF_TEST_ENTITY (substring en el nombre, opcional)
    """
    if not is_test_mode():
        return entities, periods

    load_dotenv()
    year = os.getenv("SIIF_TEST_YEAR", str(START_YEAR))
    month = os.getenv("SIIF_TEST_MONTH", "01").zfill(2)
    max_entities = int(os.getenv("SIIF_TEST_MAX_ENTITIES", "1"))
    entity_filter = os.getenv("SIIF_TEST_ENTITY", "").strip()

    filtered = list(entities)
    if entity_filter:
        filtered = [e for e in filtered if entity_filter.lower() in e.lower()]
    elif not entity_filter:
        # La entidad agregada "0 ADMINISTRACION..." suele fallar al abrir el formulario en frío.
        non_aggregate = [e for e in filtered if not e.strip().startswith("0 ADMINISTRACION")]
        if non_aggregate:
            filtered = non_aggregate
    filtered = filtered[:max_entities]

    test_periods = [{"year": year, "months": [month]}]
    print(
        f"[MODO TEST] entidades={len(filtered)} | "
        f"periodo={year}-{month} | filtro='{entity_filter or '*'}'"
    )
    if filtered:
        print(f"[MODO TEST] entidades: {filtered}")
    return filtered, test_periods


def enable_test_mode(
    year=None,
    month="01",
    max_entities=1,
    entity_contains="",
):
    os.environ["SIIF_TEST_MODE"] = "1"
    if year:
        os.environ["SIIF_TEST_YEAR"] = str(year)
    os.environ["SIIF_TEST_MONTH"] = str(month).zfill(2)
    os.environ["SIIF_TEST_MAX_ENTITIES"] = str(max_entities)
    if entity_contains:
        os.environ["SIIF_TEST_ENTITY"] = entity_contains
