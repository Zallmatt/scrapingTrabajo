"""
Pipeline SIIF Gastos: rf604m + rf610m + rf610mfte.

Recomendado en dos fases (la descarga tarda mucho; la carga es rápida):
  py -3 siif/run_all_gastos.py --solo-descarga
  py -3 siif/run_all_gastos.py --solo-carga

Continuar desde un reporte (omite los anteriores):
  py -3 siif/run_all_gastos.py --solo-descarga --desde rf610m

Un reporte puntual:
  py -3 siif/run_all_gastos.py --solo-descarga --solo rf610m

Todo junto (descarga + transform + load por reporte):
  py -3 siif/run_all_gastos.py
"""
import argparse
import importlib.util
import os
import sys
import time
import traceback

SIIF_DIR = os.path.dirname(os.path.abspath(__file__))
if SIIF_DIR not in sys.path:
    sys.path.insert(0, SIIF_DIR)

from shared.login import close_siif_session
from shared.test_limits import enable_test_mode

SCRAPERS = (
    ("scrap_CopaGastos_rf604m", "rf604m"),
    ("scrap_CopaGastos_rf610m", "rf610m"),
    ("scrap_CopaGastos_rf610mfte", "rf610mfte"),
)
SCRAPER_LABELS = {label: folder for folder, label in SCRAPERS}


def _resolve_scrapers(solo=None, desde=None):
    scrapers = SCRAPERS
    if desde:
        labels = [label for _, label in scrapers]
        if desde not in labels:
            raise ValueError(f"Reporte desconocido: {desde}")
        start = labels.index(desde)
        scrapers = scrapers[start:]
    if not solo:
        return scrapers
    selected = []
    for label in solo:
        folder = SCRAPER_LABELS.get(label)
        if not folder:
            raise ValueError(f"Reporte desconocido: {label}")
        selected.append((folder, label))
    return tuple(selected)


def _load_module(folder_name, relative_path, module_label):
    path = os.path.join(SIIF_DIR, folder_name, *relative_path.split("/"))
    spec = importlib.util.spec_from_file_location(module_label, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fmt_elapsed(seconds):
    seconds = int(max(0, seconds))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return f"{hours}h {minutes:02d}m {secs:02d}s"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def run_extract(scrapers=SCRAPERS):
    print("=== Fase 1: descarga (una sesión SIIF, un reCAPTCHA) ===")
    started = time.time()
    driver = None
    try:
        for index, (folder, label) in enumerate(scrapers):
            report_started = time.time()
            print(f"\n--- Descargando {label} ---")
            extract_mod = _load_module(folder, "etl/extract.py", f"{label}.extract")
            keep_open = index < len(scrapers) - 1
            driver = extract_mod.login_and_extract(driver=driver, keep_session=keep_open)
            print(f"--- {label} terminó en {_fmt_elapsed(time.time() - report_started)} ---")
        print(f"\n=== Descargas completadas en {_fmt_elapsed(time.time() - started)} ===")
    except Exception as exc:
        print(f"Error en descarga tras {_fmt_elapsed(time.time() - started)}: {exc}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        if driver is not None:
            close_siif_session(driver)


def run_load(scrapers=SCRAPERS):
    print("=== Fase 2: transform + carga a base ===")
    try:
        for folder, label in scrapers:
            print(f"\n--- Procesando {label} ---")
            transform_mod = _load_module(folder, "etl/transform.py", f"{label}.transform")
            load_mod = _load_module(folder, "etl/load.py", f"{label}.load")
            print(f"[transform] {label}")
            transform_mod.transform_all_files()
            print(f"[load] {label}")
            load_mod.load_to_db()
        print("\n=== Carga completada ===")
    except Exception as exc:
        print(f"Error en carga: {exc}")
        traceback.print_exc()
        sys.exit(1)


def _print_full_banner(scrapers):
    labels = ", ".join(label for _, label in scrapers)
    print("=" * 60)
    print("  Actualizar Copa Gastos SIIF")
    print(f"  Reportes: {labels}")
    print("  Flujo: descarga -> transform -> UPSERT")
    print("  Captcha: resolvelo en Chrome e Ingresar;")
    print("           despues el proceso sigue solo.")
    print("=" * 60)


def run_full(scrapers=SCRAPERS):
    _print_full_banner(scrapers)
    print("=== Pipeline completo (descarga + carga por reporte) ===")
    driver = None
    try:
        for index, (folder, label) in enumerate(scrapers):
            print(f"\n--- Reporte {label} ---")
            extract_mod = _load_module(folder, "etl/extract.py", f"{label}.extract")
            transform_mod = _load_module(folder, "etl/transform.py", f"{label}.transform")
            load_mod = _load_module(folder, "etl/load.py", f"{label}.load")

            keep_open = index < len(scrapers) - 1
            driver = extract_mod.login_and_extract(driver=driver, keep_session=keep_open)

            print(f"[transform] {label}")
            transform_mod.transform_all_files()
            print(f"[load] {label}")
            load_mod.load_to_db()
        print("\n=== Pipeline completado ===")
    except Exception as exc:
        print(f"Error: {exc}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        if driver is not None:
            close_siif_session(driver)


def main():
    parser = argparse.ArgumentParser(description="Pipeline SIIF Copa Gastos")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--solo-descarga",
        action="store_true",
        help="Solo descarga los reportes (recomendado primero)",
    )
    group.add_argument(
        "--solo-carga",
        action="store_true",
        help="Solo transform + load (cuando ya están los .xls)",
    )
    parser.add_argument(
        "--solo",
        nargs="+",
        choices=["rf604m", "rf610m", "rf610mfte"],
        help="Uno o más reportes (ej: --solo rf610m rf610mfte)",
    )
    parser.add_argument(
        "--desde",
        choices=["rf604m", "rf610m", "rf610mfte"],
        help="Arrancar desde este reporte (omite los anteriores)",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Prueba acotada: 1 entidad, 2025-01 (validar selectores)",
    )
    parser.add_argument(
        "--test-entidad",
        default="",
        help="Filtrar entidad por texto (ej: HACIENDA). Solo con --test",
    )
    args = parser.parse_args()

    scrapers = _resolve_scrapers(solo=args.solo, desde=args.desde)

    if args.test:
        enable_test_mode(year=2025, month="01", max_entities=1, entity_contains=args.test_entidad)
        print("Modo prueba: 1 entidad, enero 2025")

    if args.solo_descarga:
        run_extract(scrapers)
    elif args.solo_carga:
        run_load(scrapers)
    else:
        run_full(scrapers)


if __name__ == "__main__":
    main()
