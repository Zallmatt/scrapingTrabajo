import os
import sys
import time
import glob
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC

import shutil
from dotenv import load_dotenv

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
from shared.test_limits import apply_test_limits
from shared.report_form import (
    apply_report_table_filter,
    click_ver_reporte,
    dismiss_no_data,
    prepare_parameter_form,
    safe_screenshot,
    select_entity_synced,
    wait_adf_idle,
    wait_report_outcome,
)

ENTIDAD_INI = (
    By.XPATH,
    "//label[contains(text(), 'Entidad Inicial')]"
    "//following::select[1] | //select[contains(@id, 'socEntidadInicial')]",
)
ENTIDAD_FIN = (
    By.XPATH,
    "//label[contains(text(), 'Entidad Final')]"
    "//following::select[1] | //select[contains(@id, 'socEntidadFinal')]",
)

def wait_for_download(download_dir, timeout=60):
    return wait_for_staging_download(timeout=timeout)

def login_and_extract(driver=None, keep_session=False):
    """
    Login (si hace falta) y extracción rf604m.
    Con keep_session=True devuelve el driver para encadenar otros reportes.
    """
    LOGIN_URL = "https://siif.cgpc.gob.ar/mainSiif/faces/login.jspx"
    creds = get_credentials()
    SLEEP_TIME = creds["sleep_before_login"]
    owns_driver = driver is None

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    download_dir = os.path.join(BASE_DIR, "files/raw")
    os.makedirs(download_dir, exist_ok=True)

    if owns_driver:
        print(f"Waiting {SLEEP_TIME} seconds before login...")
        time.sleep(SLEEP_TIME)
        print(f"Starting extraction from {LOGIN_URL}")
        driver = create_chrome_driver(download_dir)
    else:
        print("Reutilizando sesión SIIF abierta (rf604m)...")

    main_window = popup_window = None
    try:
        if owns_driver:
            login_siif_selenium(driver, download_dir, typing_mode="js")

        main_window, popup_window, wait = ensure_reportes_popup(driver, download_dir)

        # Select Module and Report
        for i in range(5):
            try:
                module_dropdown = wait.until(EC.presence_of_element_located((By.ID, "pt1:socModulo::content")))
                select = Select(module_dropdown)
                select.select_by_visible_text("SUB - SISTEMA DE CONTROL DE GASTOS")
                print("Module selected.")
                time.sleep(3)
                
                apply_report_table_filter(wait, driver, "rf604m")
                
                # IMPORTANT: Click the row with the text rf604m
                report_row = wait.until(EC.element_to_be_clickable((By.XPATH, "//tr[td[contains(., 'rf604m')]]")))
                report_row.click()
                print("Report row selected.")
                time.sleep(1)
                
                # Click Siguiente
                siguiente_btn = wait.until(EC.element_to_be_clickable((By.LINK_TEXT, "Siguiente")))
                siguiente_btn.click()
                print("Clicked Siguiente.")
                time.sleep(5)
                driver.save_screenshot(os.path.join(download_dir, "parameters_debug.png"))
                prepare_parameter_form(wait, driver, ENTIDAD_FIN)
                break
            except Exception as e:
                if i == 4: 
                    driver.save_screenshot(os.path.join(download_dir, f"report_selection_error_{i}.png"))
                    raise e
                print(f"Retrying report selection (attempt {i+1}) due to: {type(e).__name__}")
                time.sleep(3)
                if len(driver.window_handles) > 1:
                    driver.switch_to.window(driver.window_handles[-1])
        
        periods = build_periods(month_mode="single")
        print(f"Periodos: {periods}")
        
        entidad_select_el = wait.until(EC.presence_of_element_located(ENTIDAD_INI))
        entidad_select = Select(entidad_select_el)
        entities = [opt.text for opt in entidad_select.options if opt.text.strip() and opt.get_attribute("value")]
        entities = skip_empty_entities(entities)
        entities, test_periods = apply_test_limits(entities, periods)
        if test_periods is not None:
            periods = test_periods
        if not entities:
            print("Sin entidades para procesar.")
            return driver if keep_session else None

        log_file = os.path.join(download_dir, "scraping_log.txt")
        with open(log_file, "a") as log:
            log.write(f"\n--- Starting Scraping Session: {time.ctime()} ---\n")

        # Process all entities
        for entity in entities:
            print(f"Processing Entity: {entity}")
            skip_entity = False
            
            for period in periods:
                if skip_entity:
                    break
                year = period["year"]
                
                try:
                    # 1. Year
                    anio_field = wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Año')]//following::input[1] | //input[contains(@id, 'txtAnioEjercicio')]")))
                    anio_field.clear()
                    anio_field.send_keys(year)
                    wait_adf_idle(driver)
                    
                    select_entity_synced(wait, driver, entity, ENTIDAD_INI, ENTIDAD_FIN)
                    
                    for month in period["months"]:
                        if skip_entity:
                            break
                        print(f"  - {year} Month: {month}")
                        
                        clean_entity = "".join([c for c in entity if c.isalnum() or c in (" ", "_")]).strip()
                        filename = f"{year}{month}_{clean_entity}.xls"
                        dest_folder = os.path.join(download_dir, year, month)
                        dest_path = os.path.join(dest_folder, filename)
                        if os.path.exists(dest_path):
                            print(f"  - Already downloaded: {dest_path}")
                            continue
                            
                        try:
                            # 3. Month (Unique field for rf604m)
                            mes_field = wait.until(EC.presence_of_element_located((By.XPATH, "//label[contains(text(), 'Mes')]//following::input[1] | //input[contains(@id, 'txtMesEjercicio')]")))
                            mes_field.clear()
                            mes_field.send_keys(month)
                            wait_adf_idle(driver)
                            
                            # Select XLS
                            try: driver.find_element(By.XPATH, "//label[contains(text(), 'XLS')]//preceding-sibling::input[1] | //input[contains(@id, 'rbtnXLS')]").click()
                            except: pass
                            
                            # Clear old stray downloads
                            clear_staging()
                                
                            current_handles_before = driver.window_handles
                            click_ver_reporte(wait, driver)
                            outcome = wait_report_outcome(driver, current_handles_before)
                            print("  - Esperando descarga o diálogo...")
                            
                            if outcome in ("no_data", "timeout"):
                                print(f"  - Sin datos para {entity} ({year}-{month}); se omite el resto de la entidad.")
                                with open(log_file, "a") as log:
                                    log.write(f"NO DATA/SKIP ENTITY: {entity} | {year}-{month}\n")
                                dismiss_no_data(driver, popup_window, current_handles_before)
                                skip_entity = True
                                break
                            
                            if outcome == "window":
                                driver.switch_to.window(driver.window_handles[-1])
                            
                            if wait_for_download(download_dir, timeout=90):
                                latest_file = latest_staging_file()
                                if not latest_file:
                                    raise FileNotFoundError("No hay archivo en staging")
                                dest_folder = os.path.join(download_dir, year, month)
                                os.makedirs(dest_folder, exist_ok=True)
                                clean_entity = "".join([c for c in entity if c.isalnum() or c in (" ", "_")]).strip()
                                filename = f"{year}{month}_{clean_entity}.xls"
                                dest_path = os.path.join(dest_folder, filename)
                                shutil.move(latest_file, dest_path)
                                print(f"  - Downloaded: {dest_path}")
                            else:
                                print(f"  - Sin descarga para {entity} ({year}-{month}); se omite el resto de la entidad.")
                                dismiss_no_data(driver, popup_window, current_handles_before)
                                skip_entity = True
                                break
                            
                            if len(driver.window_handles) > len(current_handles_before):
                                driver.close()
                                driver.switch_to.window(popup_window)
                                
                        except Exception as e:
                            print(f"  - Error processing month {month}: {e}")
                            with open(log_file, "a") as log:
                                log.write(f"ERROR_MONTH: {entity} | {year}-{month} | {str(e)[:50]}\n")
                            for h in driver.window_handles:
                                if h == popup_window:
                                    driver.switch_to.window(h)
                                    break
                            time.sleep(5)
                except Exception as e:
                    print(f"  - Error processing year {year}: {e}")
                    time.sleep(5)

    except Exception as e:
        print(f"An error occurred: {e}")
        try: driver.save_screenshot(os.path.join(download_dir, "error_screenshot.png"))
        except: pass
        raise e
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
