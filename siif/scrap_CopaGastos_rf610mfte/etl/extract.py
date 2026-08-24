"""Extracción rf610mfte via SIIF (Selenium).

Parámetros del reporte:
  - año ejercicio
  - entidad inicial / final (misma entidad)
  - código fuente (siempre 10)
  - mes desde / mes hasta (mes a mes por defecto; rango anual opcional)
"""
import glob
import os
import shutil
import sys
import time

from dotenv import load_dotenv
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

load_dotenv()

SIIF_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if SIIF_DIR not in sys.path:
    sys.path.insert(0, SIIF_DIR)

from shared.chrome import create_chrome_driver, get_staging_dir
from shared.downloads import clear_staging, latest_staging_file, wait_for_staging_download
from shared.login import (
    close_siif_session,
    ensure_reportes_popup,
    get_credentials,
    login_siif_selenium,
    return_to_report_list,
)
from shared.periods import build_periods, skip_empty_entities
from shared.report_form import (
    apply_report_table_filter,
    click_ver_reporte,
    close_newer_windows,
    dismiss_no_data,
    fill_input_adf,
    focus_handle,
    is_no_data_dialog,
    list_handles,
    prepare_parameter_form,
    safe_screenshot,
    select_entity_synced,
    wait_adf_idle,
    wait_report_outcome,
)
from shared.test_limits import apply_test_limits

CODIGO_FUENTE = "10"
REPORT_FILTER = "rf610mfte"

ENTIDAD_INI = (By.ID, "pt1:socEntidadInicial::content")
ENTIDAD_FIN = (By.ID, "pt1:socEntidadFinal::content")
ANIO = (By.ID, "pt1:txtAnioEjercicio::content")
MES_DESDE = (By.ID, "pt1:txtMesDesde::content")
MES_HASTA = (By.ID, "pt1:txtMesHasta::content")
SKIP_INPUT_IDS = ("anio", "ejercicio", "mesdesde", "meshasta", "entidad", "afrfilter", "rbtn")
FUENTE_LABEL_ID = "pt1:itCodigoFuente::content"
FUENTE_VALUE_ID = "pt1:inputText3::content"
FUENTE_CELL_XPATH = (
    "/html/body/div[1]/form/div[1]/div[5]/div/div[1]/div[2]/div/div[2]/div/div[15]"
    "/table/tbody/tr/td[2]"
)
FUENTE_INPUT_XPATH = FUENTE_CELL_XPATH + "/table/tbody/tr/td[2]/input"
XPATH_XLS = (
    "//label[text()='XLS'] | //span[text()='XLS']"
    " | //input[contains(@id, 'rbtnXLS')]"
)
XPATH_VER_REPORTE = (
    "//a[contains(., 'Ver Reporte')] | //span[contains(text(), 'Ver Reporte')]"
)


def wait_for_download(download_dir, timeout=90):
    return wait_for_staging_download(timeout=timeout)


def clean_entity_name(entity):
    return "".join(c for c in entity if c.isalnum() or c in (" ", "_")).strip()


def dest_path(download_dir, year, month_label, entity, month_mode):
    clean = clean_entity_name(entity)
    if month_mode == "range":
        folder = os.path.join(download_dir, year)
        filename = f"{year}_FTE{CODIGO_FUENTE}_{clean}.xls"
    else:
        folder = os.path.join(download_dir, year, month_label)
        filename = f"{year}{month_label}_FTE{CODIGO_FUENTE}_{clean}.xls"
    return os.path.join(folder, filename)


def entity_already_complete(download_dir, entity, periods, month_mode):
    for period in periods:
        year = period["year"]
        if month_mode == "range":
            if not os.path.exists(dest_path(download_dir, year, period["desde"], entity, month_mode)):
                return False
        else:
            for month in period["months"]:
                if not os.path.exists(dest_path(download_dir, year, month, entity, month_mode)):
                    return False
    return True


def _is_skipped_input(eid):
    low = (eid or "").lower()
    return any(token in low for token in SKIP_INPUT_IDS)


def _dump_form_inputs(driver, download_dir):
    rows = []
    for el in driver.find_elements(By.CSS_SELECTOR, "input, select, textarea"):
        try:
            if not el.is_displayed():
                continue
            rows.append(
                f"{el.tag_name} id={el.get_attribute('id')!r} "
                f"name={el.get_attribute('name')!r} "
                f"value={el.get_attribute('value')!r}"
            )
        except Exception:
            continue
    log_path = os.path.join(download_dir, "fuente_inputs.txt")
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(rows) or "(sin inputs visibles)")
    print(f"  - Inputs visibles guardados en {log_path}")
    for row in rows[:20]:
        print(f"    {row}")
    safe_screenshot(driver, os.path.join(download_dir, "fuente_debug.png"))


def _find_fuente_input(driver):
    """Busca el input de código fuente por id o por la etiqueta del formulario."""
    for el in driver.find_elements(By.CSS_SELECTOR, "input[id*='::content']"):
        try:
            eid = el.get_attribute("id") or ""
            if not el.is_displayed() or _is_skipped_input(eid):
                continue
            if "fuente" in eid.lower() or "fte" in eid.lower() or "finan" in eid.lower():
                return el
        except Exception:
            continue

    found = driver.execute_script(
        """
        const labels = Array.from(document.querySelectorAll('label, td, span, div'));
        for (const lab of labels) {
            const t = (lab.innerText || lab.textContent || '').replace(/\\s+/g, ' ').trim();
            if (!t || t.length > 60) continue;
            if (!/fuente/i.test(t)) continue;
            if (!/c[oó]digo|cod\\.?/i.test(t) && t.toLowerCase() !== 'fuente') continue;
            const row = lab.closest('tr') || lab.parentElement;
            if (!row) continue;
            const input = row.querySelector("input[id*='::content'], input");
            if (input && input.offsetParent !== null) return input;
        }
        return null;
        """
    )
    return found


def set_codigo_fuente(wait, driver, download_dir=None):
    """Activa la celda ADF de código fuente y escribe 10 en el input."""
    wait_adf_idle(driver)

    cell = None
    for xpath in (
        FUENTE_CELL_XPATH,
        f"//input[@id='{FUENTE_VALUE_ID}']/ancestor::td[1]",
        f"//input[@id='{FUENTE_LABEL_ID}']/following::td[1]",
    ):
        try:
            cell = driver.find_element(By.XPATH, xpath)
            if cell.is_displayed():
                break
        except Exception:
            cell = None
    if cell is None:
        if download_dir:
            _dump_form_inputs(driver, download_dir)
        raise RuntimeError("No se encontró la celda de código fuente")

    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", cell)
    time.sleep(0.3)
    try:
        ActionChains(driver).move_to_element(cell).pause(0.2).click().perform()
    except Exception:
        driver.execute_script("arguments[0].click();", cell)
    print("  - Clic en celda de código fuente")
    time.sleep(0.8)
    wait_adf_idle(driver)

    field = None
    short_wait = WebDriverWait(driver, 8)
    for locator in (
        (By.ID, FUENTE_VALUE_ID),
        (By.XPATH, FUENTE_INPUT_XPATH),
        (By.XPATH, FUENTE_CELL_XPATH + "//input[not(contains(@id, 'itCodigoFuente'))]"),
    ):
        try:
            field = short_wait.until(EC.element_to_be_clickable(locator))
            break
        except Exception:
            field = None
    if field is None:
        if download_dir:
            _dump_form_inputs(driver, download_dir)
        raise RuntimeError("Después del clic no apareció el input de código fuente")

    print(f"  - Input código fuente: {field.get_attribute('id')}")
    field.click()
    field.send_keys(Keys.CONTROL + "a")
    field.send_keys(Keys.DELETE)
    field.send_keys(CODIGO_FUENTE)
    field.send_keys(Keys.TAB)
    wait_adf_idle(driver)

    value_field = driver.find_element(By.ID, FUENTE_VALUE_ID)
    written = (value_field.get_attribute("value") or "").strip()
    if written != CODIGO_FUENTE:
        if download_dir:
            _dump_form_inputs(driver, download_dir)
        raise RuntimeError(f"Código fuente quedó '{written}', se esperaba '{CODIGO_FUENTE}'")
    print(f"  - Código fuente ingresado: {CODIGO_FUENTE}")


def fill_report_fields(wait, driver, entity, year, mes_desde, mes_hasta, download_dir=None):
    fill_input_adf(wait, driver, ANIO, year)
    select_entity_synced(wait, driver, entity, ENTIDAD_INI, ENTIDAD_FIN)
    set_codigo_fuente(wait, driver, download_dir=download_dir)
    wait.until(EC.element_to_be_clickable(MES_DESDE))
    fill_input_adf(wait, driver, MES_DESDE, mes_desde)
    fill_input_adf(wait, driver, MES_HASTA, mes_hasta)
    print(f"  - Mes desde/hasta = {mes_desde}/{mes_hasta}")
    wait_adf_idle(driver)


def select_report_rf610mfte(wait, driver, download_dir):
    for attempt in range(5):
        try:
            module_dropdown = wait.until(EC.presence_of_element_located((By.ID, "pt1:socModulo::content")))
            Select(module_dropdown).select_by_visible_text("SUB - SISTEMA DE CONTROL DE GASTOS")
            time.sleep(3)

            apply_report_table_filter(wait, driver, REPORT_FILTER)

            wait.until(EC.element_to_be_clickable((By.XPATH, f"//tr[td[contains(., '{REPORT_FILTER}')]]"))).click()
            time.sleep(1)
            wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Siguiente"))).click()
            print("Reporte rf610mfte seleccionado.")
            prepare_parameter_form(wait, driver, ENTIDAD_FIN)
            return
        except Exception as exc:
            if attempt == 4:
                driver.save_screenshot(os.path.join(download_dir, "report_selection_error.png"))
                raise exc
            print(f"Reintento selección reporte ({attempt + 1}/5)...")
            time.sleep(3)
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])


def download_one(driver, wait, popup_window, download_dir, log_file, entity, year, mes_desde, mes_hasta, month_mode):
    label = mes_desde if mes_desde == mes_hasta else f"{mes_desde}-{mes_hasta}"
    target = dest_path(download_dir, year, mes_desde, entity, month_mode)

    if os.path.exists(target):
        print(f"  - Ya existe: {target}")
        return "ok", popup_window

    print(f"  - {year} | fuente {CODIGO_FUENTE} | mes {label} | {entity}")

    try:
        popup_window = focus_handle(driver, popup_window)
        if not popup_window:
            return "dead", None

        fill_report_fields(wait, driver, entity, year, mes_desde, mes_hasta, download_dir=download_dir)

        try:
            driver.find_element(By.XPATH, XPATH_XLS).click()
        except Exception:
            pass

        clear_staging()

        handles_before = list_handles(driver)
        click_ver_reporte(wait, driver, XPATH_VER_REPORTE)
        outcome = wait_report_outcome(driver, handles_before)

        if outcome == "no_data" or (outcome == "timeout" and is_no_data_dialog(driver)):
            print(f"  - Sin datos para {entity} ({year}-{label}); se omite el resto de la entidad.")
            with open(log_file, "a", encoding="utf-8") as log:
                log.write(f"NO DATA/SKIP ENTITY: {entity} | {year}-{label} | FTE{CODIGO_FUENTE}\n")
            dismiss_no_data(driver, popup_window, handles_before)
            popup_window = focus_handle(driver, popup_window)
            return "skip_entity", popup_window

        if outcome == "timeout":
            print(f"  - Timeout sin diálogo en {entity} ({year}-{label}); se sigue con el mes siguiente.")
            dismiss_no_data(driver, popup_window, handles_before)
            popup_window = focus_handle(driver, popup_window)
            return "ok", popup_window

        if outcome == "window":
            focus_handle(driver, None)

        if wait_for_download(download_dir):
            latest = latest_staging_file()
            if not latest:
                raise FileNotFoundError("No hay archivo en staging")
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.move(latest, target)
            print(f"  - Descargado: {target}")
        else:
            print(f"  - Sin archivo para {entity} ({year}-{label}); se sigue con el mes siguiente.")
            dismiss_no_data(driver, popup_window, handles_before)

        popup_window = close_newer_windows(driver, popup_window)
        return "ok", popup_window

    except Exception as exc:
        print(f"  - Error: {exc}")
        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"ERROR: {entity} | {year}-{label} | {str(exc)[:80]}\n")
        if "no such window" in str(exc).lower() or "web view not found" in str(exc).lower():
            return "dead", None
        popup_window = focus_handle(driver, popup_window)
        time.sleep(2)
        return "error", popup_window


def login_and_extract(driver=None, keep_session=False):
    creds = get_credentials()
    month_mode = os.getenv("SIIF_MONTH_MODE", "single").lower()
    owns_driver = driver is None

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    download_dir = os.path.join(base_dir, "files/raw")
    os.makedirs(download_dir, exist_ok=True)

    if owns_driver:
        print(f"Esperando {creds['sleep_before_login']}s antes del login...")
        time.sleep(creds["sleep_before_login"])
        driver = create_chrome_driver(download_dir)
    else:
        print("Reutilizando sesión SIIF abierta (rf610mfte)...")

    main_window = popup_window = None
    try:
        if owns_driver:
            login_siif_selenium(driver, download_dir, typing_mode="js")

        main_window, popup_window, wait = ensure_reportes_popup(driver, download_dir)
        select_report_rf610mfte(wait, driver, download_dir)
        prepare_parameter_form(wait, driver, ENTIDAD_FIN)

        try:
            driver.find_element(By.XPATH, XPATH_XLS).click()
        except Exception:
            pass

        periods = build_periods(month_mode=month_mode if month_mode in ("single", "range") else "single")

        entidad_el = wait.until(EC.presence_of_element_located(ENTIDAD_INI))
        entities = [
            opt.text.strip()
            for opt in Select(entidad_el).options
            if opt.text.strip() and opt.get_attribute("value")
        ]
        entities = skip_empty_entities(entities)
        entities, test_periods = apply_test_limits(entities, periods)
        if test_periods is not None:
            periods = test_periods
        print(f"Modo mes: {month_mode} | periodos: {periods}")
        if not entities:
            print("Sin entidades para procesar.")
            return driver if keep_session else None

        log_file = os.path.join(download_dir, "scraping_log.txt")
        with open(log_file, "a", encoding="utf-8") as log:
            log.write(f"\n--- rf610mfte {time.ctime()} | modo={month_mode} ---\n")

        for entity in entities:
            if entity_already_complete(download_dir, entity, periods, month_mode):
                print(f"Entidad completa, se omite: {entity}")
                continue
            print(f"Entidad: {entity}")
            skip_entity = False
            for period in periods:
                if skip_entity:
                    break
                year = period["year"]
                months = [period["desde"]] if month_mode == "range" else period["months"]
                hastas = [period["hasta"]] if month_mode == "range" else period["months"]
                try:
                    for mes_desde, mes_hasta in zip(months, hastas):
                        if skip_entity:
                            break
                        result, popup_window = download_one(
                            driver,
                            wait,
                            popup_window,
                            download_dir,
                            log_file,
                            entity,
                            year,
                            mes_desde,
                            mes_hasta,
                            month_mode,
                        )
                        if result == "dead":
                            print("Ventana cerrada; reabriendo REPORTES...")
                            main_window, popup_window, wait = ensure_reportes_popup(driver, download_dir)
                            select_report_rf610mfte(wait, driver, download_dir)
                            prepare_parameter_form(wait, driver, ENTIDAD_FIN)
                            result, popup_window = download_one(
                                driver,
                                wait,
                                popup_window,
                                download_dir,
                                log_file,
                                entity,
                                year,
                                mes_desde,
                                mes_hasta,
                                month_mode,
                            )
                        if result == "skip_entity":
                            skip_entity = True
                            break
                except Exception as exc:
                    print(f"  - Error año {year}: {exc}")
                    if "no such window" in str(exc).lower():
                        try:
                            main_window, popup_window, wait = ensure_reportes_popup(driver, download_dir)
                            select_report_rf610mfte(wait, driver, download_dir)
                            prepare_parameter_form(wait, driver, ENTIDAD_FIN)
                        except Exception as recover_exc:
                            print(f"  - No se pudo reabrir REPORTES: {recover_exc}")
                            raise
                    time.sleep(2)

    except Exception as exc:
        print(f"Error en extracción rf610mfte: {exc}")
        try:
            driver.save_screenshot(os.path.join(download_dir, "error_screenshot.png"))
        except Exception:
            pass
        raise
    finally:
        if not keep_session:
            close_siif_session(driver)

    if keep_session:
        return_to_report_list(driver, popup_window)
        print("Popup REPORTES abierto para el siguiente reporte.")
        return driver
    return None


if __name__ == "__main__":
    login_and_extract()
