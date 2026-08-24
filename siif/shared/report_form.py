"""Utilidades compartidas para formularios de reportes SIIF (Oracle ADF)."""
import time

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

NO_DATA_XPATHS = (
    "//*[contains(text(), 'No se encontraron datos para el reporte seleccionado')]",
    "//*[contains(text(), 'No se encontraron datos')]",
)

ADF_BUSY_XPATH = (
    "//*[contains(@class, 'Busy') and contains(@class, 'Indicator')]",
    "//div[contains(@id, '__af_B') and contains(@style, 'visibility: visible')]",
)

REPORT_FILTER_NAME_ID = "_afrFilterpt1_afr_pc1_afr_tableReportes_afr_c2::content"
REPORT_FILTER_CODE_ID = "_afrFilterpt1_afr_pc1_afr_tableReportes_afr_c1::content"


def _read_filter_value(field):
    return (field.get_attribute("value") or "").strip()


def _reset_adf_filter_field(driver, field, confirm_enter=True):
    """Vacía por completo un filtro ADF antes de escribir otro valor."""
    field.click()
    time.sleep(0.2)

    try:
        field.clear()
    except Exception:
        pass

    driver.execute_script(
        """
        const el = arguments[0];
        el.value = '';
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
        """,
        field,
    )

    field.send_keys(Keys.CONTROL + "a")
    field.send_keys(Keys.DELETE)

    remaining = _read_filter_value(field)
    if remaining:
        for _ in range(len(remaining) + 10):
            field.send_keys(Keys.BACKSPACE)
        remaining = _read_filter_value(field)

    if remaining:
        raise RuntimeError(f"No se pudo limpiar el filtro (quedó: '{remaining}')")

    if confirm_enter:
        field.send_keys(Keys.ENTER)
        time.sleep(0.4)

    return field


def _fill_adf_filter_field(driver, field, text):
    """Limpia y escribe un valor nuevo en el filtro."""
    _reset_adf_filter_field(driver, field, confirm_enter=False)
    field.send_keys(text)
    written = _read_filter_value(field)
    if written != text:
        _reset_adf_filter_field(driver, field, confirm_enter=False)
        driver.execute_script(
            """
            const el = arguments[0];
            const val = arguments[1];
            el.value = val;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            field,
            text,
        )
        written = _read_filter_value(field)
    if written != text:
        raise RuntimeError(f"Filtro incompleto: esperado '{text}', quedó '{written}'")
    field.send_keys(Keys.ENTER)
    return field


def clear_report_table_filters(driver):
    """Limpia filtros de código y nombre en la grilla de reportes."""
    cleared = 0
    for fid in (REPORT_FILTER_CODE_ID, REPORT_FILTER_NAME_ID):
        try:
            field = driver.find_element(By.ID, fid)
            if not _read_filter_value(field):
                continue
            _reset_adf_filter_field(driver, field, confirm_enter=True)
            cleared += 1
        except Exception:
            continue
    if cleared:
        wait_adf_idle(driver)
        print("Filtros de la tabla de reportes limpiados.")
    return cleared


def apply_report_table_filter(wait, driver, text, row_match=None, settle_seconds=5):
    """Filtra la tabla por nombre de reporte (columna c2) y confirma con Enter."""
    row_match = row_match or text
    clear_report_table_filters(driver)
    filter_field = wait.until(EC.presence_of_element_located((By.ID, REPORT_FILTER_NAME_ID)))
    _fill_adf_filter_field(driver, filter_field, text)
    print(f"Filtro aplicado: '{text}' + Enter")
    wait_adf_idle(driver)
    time.sleep(settle_seconds)
    wait.until(EC.element_to_be_clickable((By.XPATH, f"//tr[td[contains(., '{row_match}')]]")))
    return filter_field


def list_handles(driver):
    try:
        return list(driver.window_handles)
    except Exception:
        return []


def focus_handle(driver, preferred=None):
    handles = list_handles(driver)
    if not handles:
        return None
    target = preferred if preferred in handles else handles[-1]
    try:
        driver.switch_to.window(target)
        return target
    except Exception:
        try:
            driver.switch_to.window(handles[-1])
            return handles[-1]
        except Exception:
            return None


def close_newer_windows(driver, keep_handle):
    for handle in list_handles(driver):
        if handle == keep_handle:
            continue
        try:
            driver.switch_to.window(handle)
            driver.close()
        except Exception:
            pass
    return focus_handle(driver, keep_handle)


def wait_adf_idle(driver, timeout=20, settle=0.8):
    """Espera a que Oracle ADF termine refrescos parciales."""
    end = time.time() + timeout
    while time.time() < end:
        busy = False
        try:
            for xpath in ADF_BUSY_XPATH:
                for el in driver.find_elements(By.XPATH, xpath):
                    try:
                        if el.is_displayed():
                            busy = True
                            break
                    except Exception:
                        pass
                if busy:
                    break
        except Exception:
            return
        if not busy:
            time.sleep(settle)
            return
        time.sleep(0.4)


def blur_form(driver):
    try:
        driver.find_element(By.TAG_NAME, "body").click()
    except Exception:
        pass


def type_in_adf_input(wait, driver, locator, text, tab_after=True):
    """Escribe en un input ADF (::content). No usa JS salvo fallback."""
    field = wait.until(EC.element_to_be_clickable(locator))
    if field.tag_name.lower() != "input":
        raise ValueError(f"Se esperaba input, encontrado: {field.tag_name}")

    field.click()
    time.sleep(0.2)
    current = (field.get_attribute("value") or "").strip()
    if current == str(text):
        if tab_after:
            field.send_keys(Keys.TAB)
        wait_adf_idle(driver)
        return field

    field.send_keys(Keys.CONTROL + "a")
    field.send_keys(Keys.DELETE)
    for char in str(text):
        field.send_keys(char)
        time.sleep(0.05)
    if tab_after:
        field.send_keys(Keys.TAB)
    wait_adf_idle(driver)

    written = (field.get_attribute("value") or "").strip()
    if written != str(text):
        raise RuntimeError(f"Input quedó en '{written}', se esperaba '{text}'")
    return field


def fill_input_adf(wait, driver, locator, value):
    """Rellena inputs Oracle ADF (incluye campos ::content no interactuables)."""
    field = wait.until(EC.presence_of_element_located(locator))
    wait_adf_idle(driver)
    text = str(value)
    try:
        target = wait.until(EC.element_to_be_clickable(locator))
        target.click()
        target.send_keys(Keys.CONTROL + "a")
        target.send_keys(Keys.BACKSPACE)
        target.send_keys(text)
        target.send_keys(Keys.TAB)
    except Exception:
        driver.execute_script(
            """
            const el = arguments[0];
            const val = arguments[1];
            el.value = val;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            """,
            field,
            text,
        )
    wait_adf_idle(driver)
    return field


def safe_screenshot(driver, path):
    try:
        driver.save_screenshot(path)
        return True
    except Exception as exc:
        print(f"No se pudo guardar screenshot ({path}): {exc}")
        return False


def is_no_data_dialog(driver):
    """Detecta el aviso ADF 'No se encontraron datos...' (visible, no HTML oculto)."""
    try:
        visible = driver.execute_script(
            "return (document.body && document.body.innerText) ? document.body.innerText : '';"
        ) or ""
        if "No se encontraron datos" in visible:
            return True
    except Exception:
        pass
    for xpath in NO_DATA_XPATHS:
        for el in driver.find_elements(By.XPATH, xpath):
            try:
                if el.is_displayed():
                    return True
            except Exception:
                pass
    return False


def dismiss_no_data(driver, popup_window, handles_before):
    try:
        btn = driver.find_element(
            By.XPATH,
            "//button[contains(., 'Aceptar')] | //span[text()='Aceptar']/ancestor::button",
        )
        btn.click()
    except Exception:
        try:
            driver.find_element(By.XPATH, "//span[text()='Aceptar']").click()
        except Exception:
            pass
    time.sleep(1)
    keep = popup_window
    try:
        if len(list_handles(driver)) > len(handles_before):
            driver.close()
    except Exception:
        pass
    keep = focus_handle(driver, keep)
    if keep:
        wait_adf_idle(driver)


def wait_report_outcome(driver, handles_before, timeout=45, min_wait=3):
    """
    Espera ventana de descarga o diálogo sin datos.

    Returns: 'window' | 'no_data' | 'timeout'
    """
    time.sleep(min_wait)
    start = time.time()
    while time.time() - start < timeout:
        if len(driver.window_handles) > len(handles_before):
            return "window"
        if is_no_data_dialog(driver):
            return "no_data"
        time.sleep(0.5)
    if is_no_data_dialog(driver):
        return "no_data"
    return "timeout"


def select_entity_synced(wait, driver, entity, ini_locator, fin_locator):
    """Selecciona entidad inicial/final y verifica que queden sincronizadas."""
    wait_adf_idle(driver)
    ini_sel = Select(wait.until(EC.presence_of_element_located(ini_locator)))
    ini_sel.select_by_visible_text(entity)
    wait_adf_idle(driver, timeout=15)

    fin_sel = Select(wait.until(EC.presence_of_element_located(fin_locator)))
    selected = fin_sel.first_selected_option.text.strip()
    if selected != entity.strip():
        fin_sel.select_by_visible_text(entity)
        wait_adf_idle(driver, timeout=15)

    ini_sel = Select(driver.find_element(*ini_locator))
    fin_sel = Select(driver.find_element(*fin_locator))
    if ini_sel.first_selected_option.text.strip() != entity.strip():
        raise RuntimeError(f"Entidad inicial no quedó en '{entity}'")
    if fin_sel.first_selected_option.text.strip() != entity.strip():
        raise RuntimeError(f"Entidad final no quedó en '{entity}'")


def prepare_parameter_form(wait, driver, fin_locator, min_options=2, extra_wait=2):
    """Espera a que el formulario de parámetros esté completamente cargado."""
    wait_adf_idle(driver)
    WebDriverWait(driver, 30).until(
        lambda d: len(Select(d.find_element(*fin_locator)).options) >= min_options
    )
    wait_adf_idle(driver)
    time.sleep(extra_wait)


def click_ver_reporte(
    wait,
    driver,
    ver_reporte_xpath="//a[contains(., 'Ver Reporte')] | //span[contains(text(), 'Ver Reporte')]",
):
    btn = wait.until(EC.element_to_be_clickable((By.XPATH, ver_reporte_xpath)))
    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
    time.sleep(0.5)
    blur_form(driver)
    wait_adf_idle(driver)
    try:
        btn.click()
    except Exception:
        driver.execute_script("arguments[0].click();", btn)
