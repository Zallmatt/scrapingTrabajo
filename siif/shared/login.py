"""Login SIIF con reCAPTCHA: credenciales automaticas, captcha manual."""
import os
import time

from dotenv import load_dotenv
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

LOGIN_URL = "https://siif.cgpc.gob.ar/mainSiif/faces/login.jspx"
MENU_SELECTORS = (
    (By.ID, "pt1:cb12"),
    (By.XPATH, "//span[contains(text(), 'REPORTES')] | //a[contains(text(), 'REPORTES')]"),
)

DISCONNECT_SELECTORS = (
    "//a[contains(translate(., 'DESCONectar', 'desconectar'), 'desconectar')]",
    "//span[contains(translate(., 'DESCONectar', 'desconectar'), 'desconectar')]/ancestor::a[1]",
    "//span[contains(translate(., 'DESCONectar', 'desconectar'), 'desconectar')]",
    "//a[contains(@title, 'esconectar')]",
    "//img[contains(translate(@alt, 'DESCONectar', 'desconectar'), 'desconectar')]/ancestor::a[1]",
)

BACK_SELECTORS = (
    "//a[contains(., 'Volver')]",
    "//span[contains(., 'Volver')]/ancestor::a[1]",
    "//span[contains(., 'Volver')]",
    "//a[contains(., 'Regresar')]",
    "//span[contains(., 'Regresar')]/ancestor::a[1]",
    "//span[contains(., 'Regresar')]",
    "//button[contains(., 'Volver')]",
    "//button[contains(., 'Regresar')]",
    "//a[contains(., 'Atrás')]",
    "//a[contains(., 'Atras')]",
    "//span[contains(., 'Atrás')]",
    "//span[contains(., 'Atras')]",
)

REPORTES_SESSION_ACTIVE_XPATHS = (
    "//*[contains(text(), \"ya tiene iniciada una sesión del módulo 'REPORTES'\")]",
    "//*[contains(text(), 'ya tiene iniciada una sesión')]",
)


def get_credentials():
    load_dotenv()
    return {
        "username": os.getenv("SIIF_USERNAME", "boscof"),
        "password": os.getenv("SIIF_PASSWORD", "IPECD2026"),
        "sleep_before_login": int(os.getenv("SIIF_SLEEP_BEFORE_LOGIN", "5")),
        "manual_login_timeout": int(os.getenv("SIIF_MANUAL_LOGIN_TIMEOUT", "600")),
    }


def is_logged_in(driver):
    try:
        if not driver.window_handles:
            return False
        url = driver.current_url or ""
        return "mainSiif" in url and "login" not in url
    except Exception:
        return False


def slow_type_default(element, text):
    element.click()
    element.send_keys(Keys.CONTROL + "a")
    element.send_keys(Keys.BACKSPACE)
    for char in text:
        element.send_keys(char)
        time.sleep(0.1)


def slow_type_js(driver, element, text):
    try:
        element.clear()
    except Exception:
        pass
    driver.execute_script("arguments[0].value = '';", element)
    element.send_keys(text)
    time.sleep(0.5)


def fill_credentials(driver, wait, username, password, typing_mode="default"):
    user_field = wait.until(EC.element_to_be_clickable((By.ID, "pt1:it1::content")))
    pass_field = wait.until(EC.element_to_be_clickable((By.ID, "pt1:it2::content")))

    if typing_mode == "js":
        slow_type_js(driver, user_field, username)
        slow_type_js(driver, pass_field, password)
    else:
        slow_type_default(user_field, username)
        slow_type_default(pass_field, password)

    print("Usuario y contraseña completados.")


def prompt_recaptcha_manual(timeout_seconds=600):
    print("")
    print("=" * 60)
    print("reCAPTCHA detectado en SIIF")
    print("1. En el navegador, completá el checkbox y las imágenes.")
    print("2. Hacé clic en Ingresar / Login.")
    print("3. Este script sigue solo cuando aparezca el menú principal.")
    print(f"   (espera máxima: {timeout_seconds} s)")
    print("=" * 60)
    print("")


def handle_active_session_dialog(driver, timeout=10):
    try:
        print("Revisando diálogo de sesión activa...")
        aceptar_btn = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable(
                (
                    By.XPATH,
                    "//button[contains(., 'Aceptar')] | //a[contains(., 'Aceptar')] | //span[text()='Aceptar']",
                )
            )
        )
        aceptar_btn.click()
        print("Diálogo de sesión activa aceptado.")
        time.sleep(5)
    except Exception:
        print("Sin diálogo de sesión activa.")


def wait_for_main_menu(driver, download_dir, timeout=60):
    print(f"Esperando menú principal (timeout {timeout}s)...")
    os.makedirs(download_dir, exist_ok=True)
    driver.save_screenshot(os.path.join(download_dir, "pre_menu_wait.png"))

    end = time.time() + timeout
    last_error = None
    while time.time() < end:
        if is_logged_in(driver):
            for by, selector in MENU_SELECTORS:
                try:
                    if driver.find_elements(by, selector):
                        print("Menú principal detectado.")
                        return
                except Exception as exc:
                    last_error = exc
        time.sleep(2)

    driver.save_screenshot(os.path.join(download_dir, "login_timeout.png"))
    raise TimeoutError(
        "No se detectó el menú principal después del login manual. "
        f"Último error: {last_error}"
    )


def login_siif_selenium(driver, download_dir, typing_mode="default"):
    """
    Completa credenciales, espera reCAPTCHA manual y confirma menú principal.
    No intenta resolver ni saltear el captcha.
    """
    creds = get_credentials()
    wait = WebDriverWait(driver, 30)

    driver.get(LOGIN_URL)
    print(f"URL actual: {driver.current_url}")

    if is_logged_in(driver):
        print("Sesión SIIF ya activa; se omite login.")
        wait_for_main_menu(driver, download_dir, timeout=30)
        return

    try:
        wait.until(EC.presence_of_element_located((By.ID, "pt1:it1::content")))
        print("Formulario de login encontrado.")
    except Exception as exc:
        driver.save_screenshot(os.path.join(download_dir, "login_error.png"))
        if is_logged_in(driver):
            print("Ya logueado tras revisar la página.")
            wait_for_main_menu(driver, download_dir, timeout=30)
            return
        raise exc

    fill_credentials(driver, wait, creds["username"], creds["password"], typing_mode)
    prompt_recaptcha_manual(creds["manual_login_timeout"])

    # El usuario resuelve reCAPTCHA y hace clic en Ingresar en el navegador.
    wait_for_main_menu(driver, download_dir, timeout=creds["manual_login_timeout"])
    handle_active_session_dialog(driver)
    wait_for_main_menu(driver, download_dir, timeout=60)
    print("Login SIIF completado.")


def close_extra_windows(driver, keep_handle):
    """Cierra popups de reportes; deja abierta la ventana principal."""
    for handle in list(driver.window_handles):
        if handle != keep_handle:
            try:
                driver.switch_to.window(handle)
                disconnect_reportes_module(driver)
                driver.close()
            except Exception:
                pass
    driver.switch_to.window(keep_handle)


def _click_first(driver, xpaths, timeout=3):
    for xpath in xpaths:
        try:
            btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", btn)
            time.sleep(0.3)
            try:
                btn.click()
            except Exception:
                driver.execute_script("arguments[0].click();", btn)
            return True
        except Exception:
            continue
    return False


def disconnect_reportes_module(driver, timeout=10):
    """Desconecta el módulo REPORTES (obligatorio antes de abrir otro reporte)."""
    if _click_first(driver, DISCONNECT_SELECTORS, timeout=timeout):
        print("Módulo REPORTES desconectado.")
        time.sleep(2)
        _click_first(
            driver,
            (
                "//button[contains(., 'Aceptar')] | //span[text()='Aceptar']",
                "//button[contains(., 'Sí')] | //span[text()='Sí']",
            ),
            timeout=3,
        )
        time.sleep(2)
        return True
    return False


def handle_reportes_session_active_dialog(driver, timeout=5):
    """Cierra el diálogo de sesión REPORTES ya abierta."""
    for xpath in REPORTES_SESSION_ACTIVE_XPATHS:
        try:
            matches = driver.find_elements(By.XPATH, xpath)
            if not any(el.is_displayed() for el in matches):
                continue
            print("SIIF indica sesión REPORTES activa; intentando liberarla...")
            _click_first(
                driver,
                (
                    "//button[contains(., 'Aceptar')] | //span[text()='Aceptar']",
                    "//a[contains(., 'Aceptar')]",
                ),
                timeout=timeout,
            )
            time.sleep(1)
            return True
        except Exception:
            continue
    return False


def is_report_list_ready(driver):
    """True si el popup está en la grilla de reportes (módulo + filtro)."""
    try:
        return bool(driver.find_elements(By.ID, "pt1:socModulo::content"))
    except Exception:
        return False


def return_to_report_list(driver, popup_window=None, timeout=8):
    """
    Vuelve a la lista de reportes con Volver/Regresar, sin cerrar la pestaña.
    """
    if popup_window and popup_window in driver.window_handles:
        driver.switch_to.window(popup_window)
    elif len(driver.window_handles) > 1:
        driver.switch_to.window(driver.window_handles[-1])

    if is_report_list_ready(driver):
        print("Ya en lista de reportes.")
        try:
            from shared.report_form import clear_report_table_filters
            clear_report_table_filters(driver)
        except Exception:
            pass
        return True

    combined = (
        "//a[contains(., 'Volver') or contains(., 'Regresar') or contains(., 'Atrás') or contains(., 'Atras')]",
        "//span[contains(., 'Volver') or contains(., 'Regresar') or contains(., 'Atrás') or contains(., 'Atras')]",
        "//button[contains(., 'Volver') or contains(., 'Regresar')]",
    )
    for _ in range(3):
        clicked = False
        for text in ("Volver", "Regresar"):
            try:
                btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.LINK_TEXT, text)))
                btn.click()
                clicked = True
                break
            except Exception:
                continue
        if not clicked:
            clicked = _click_first(driver, combined, timeout=2)
        if not clicked:
            break
        print("Clic en Volver/Regresar.")
        time.sleep(2)
        if is_report_list_ready(driver):
            print("Lista de reportes lista (sin cerrar pestaña).")
            try:
                from shared.report_form import clear_report_table_filters
                clear_report_table_filters(driver)
            except Exception:
                pass
            return True

    if is_report_list_ready(driver):
        try:
            from shared.report_form import clear_report_table_filters
            clear_report_table_filters(driver)
        except Exception:
            pass
        return True
    print("No se encontró Volver/Regresar; se mantiene el popup actual.")
    return False


def release_reportes_module(driver, main_window=None, popup_window=None):
    """
    Libera la sesión del módulo REPORTES en el servidor.
    Usar solo al terminar toda la sesión, no entre reportes.
    """
    if not driver.window_handles:
        return False

    if main_window is None:
        main_window = driver.window_handles[0]

    targets = []
    if popup_window and popup_window in driver.window_handles:
        targets.append(popup_window)
    for handle in driver.window_handles:
        if handle != main_window and handle not in targets:
            targets.append(handle)

    disconnected = False
    for handle in targets:
        try:
            driver.switch_to.window(handle)
            if disconnect_reportes_module(driver):
                disconnected = True
        except Exception:
            pass

    close_extra_windows(driver, main_window)
    driver.switch_to.window(main_window)
    if disconnected:
        print("Sesión del módulo REPORTES liberada.")
    else:
        print(
            "No se pudo desconectar REPORTES desde el popup. "
            "Si falla el siguiente reporte, esperá ~10 min o reiniciá el pipeline."
        )
    return disconnected


def _open_reportes_menu(wait, driver, main_window=None):
    try:
        wait.until(EC.element_to_be_clickable((By.ID, "pt1:cb12"))).click()
    except Exception:
        wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//span[contains(text(), 'REPORTES')] | //a[contains(text(), 'REPORTES')]")
            )
        ).click()
    time.sleep(1)
    if handle_reportes_session_active_dialog(driver):
        if main_window is not None:
            release_reportes_module(driver, main_window)
            time.sleep(2)
            try:
                wait.until(EC.element_to_be_clickable((By.ID, "pt1:cb12"))).click()
            except Exception:
                wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//span[contains(text(), 'REPORTES')] | //a[contains(text(), 'REPORTES')]")
                    )
                ).click()
            time.sleep(1)
            if handle_reportes_session_active_dialog(driver):
                raise RuntimeError(
                    "SIIF mantiene una sesión REPORTES abierta. "
                    "Usá 'Desconectar' en el módulo o esperá unos minutos."
                )
        else:
            raise RuntimeError(
                "SIIF mantiene una sesión REPORTES abierta. "
                "Usá 'Desconectar' en el módulo o esperá unos minutos."
            )
    wait.until(EC.element_to_be_clickable((By.ID, "pt1:cb14"))).click()


def return_to_main_menu(driver, timeout=30):
    """Vuelve al menú principal para lanzar otro reporte en la misma sesión."""
    wait = WebDriverWait(driver, timeout)
    main_window = driver.window_handles[0]
    close_extra_windows(driver, main_window)

    for by, selector in MENU_SELECTORS:
        try:
            if driver.find_elements(by, selector):
                print("Ya en menú principal.")
                return main_window
        except Exception:
            pass

    driver.get(LOGIN_URL.replace("login.jspx", "home.jspx"))
    time.sleep(3)
    if not is_logged_in(driver):
        driver.get(LOGIN_URL)
        time.sleep(2)

    wait.until(EC.presence_of_element_located(MENU_SELECTORS[0]))
    print("Menú principal listo para otro reporte.")
    return main_window


def navigate_to_reportes_popup(driver, download_dir, timeout=30):
    """Menú REPORTES -> Reportes y devuelve (main_window, popup_window, wait)."""
    wait = WebDriverWait(driver, timeout)
    main_window = return_to_main_menu(driver, timeout)

    _open_reportes_menu(wait, driver, main_window)
    time.sleep(2)

    wait.until(lambda d: len(d.window_handles) > 1)
    for handle in driver.window_handles:
        if handle != main_window:
            driver.switch_to.window(handle)
            break

    time.sleep(3)
    os.makedirs(download_dir, exist_ok=True)
    driver.save_screenshot(os.path.join(download_dir, "popup_debug.png"))
    popup_window = driver.current_window_handle
    print("Popup de reportes abierto.")
    return main_window, popup_window, wait


def ensure_reportes_popup(driver, download_dir, timeout=30):
    """Reutiliza el popup de REPORTES si ya está abierto; si no, lo abre."""
    wait = WebDriverWait(driver, timeout)
    if len(driver.window_handles) > 1:
        main_window = driver.window_handles[0]
        popup_window = None
        for handle in driver.window_handles:
            if handle != main_window:
                driver.switch_to.window(handle)
                popup_window = handle
                break
        if popup_window is None:
            popup_window = driver.current_window_handle
        if not is_report_list_ready(driver):
            return_to_report_list(driver, popup_window)
        print("Reutilizando popup de REPORTES (misma pestaña).")
        return main_window, popup_window, wait
    return navigate_to_reportes_popup(driver, download_dir, timeout)


def logout_siif_selenium(driver, timeout=15):
    """Cierra sesión en el servidor antes de apagar el navegador."""
    if not is_logged_in(driver):
        print("Sin sesión SIIF activa; se omite logout.")
        return

    main_window = driver.window_handles[0]
    close_extra_windows(driver, main_window)

    logout_selectors = (
        "//a[contains(., 'Cerrar') and contains(., 'sesi')]",
        "//span[contains(., 'Cerrar') and contains(., 'sesi')]",
        "//a[contains(., 'Salir')]",
        "//span[contains(., 'Salir')]",
        "//a[contains(@title, 'Salir')]",
    )

    for xpath in logout_selectors:
        try:
            btn = WebDriverWait(driver, timeout).until(
                EC.element_to_be_clickable((By.XPATH, xpath))
            )
            btn.click()
            print("Sesión SIIF cerrada correctamente.")
            time.sleep(3)
            return
        except Exception:
            continue

    print("No se encontró botón de cerrar sesión; el servidor puede retener la sesión ~10 min.")


def close_siif_session(driver, logout=True):
    """Logout explícito y cierre del navegador."""
    if logout:
        try:
            logout_siif_selenium(driver)
        except Exception as exc:
            print(f"Logout falló: {exc}")
    try:
        driver.quit()
    except Exception:
        pass
    print("Navegador cerrado.")
