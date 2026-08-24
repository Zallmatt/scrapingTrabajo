"""Arranque de Chrome para scrapers SIIF (sin webdriver-manager / GitHub)."""
import os
import time

from selenium import webdriver
from selenium_stealth import stealth

SIIF_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STAGING_DIR = os.path.join(SIIF_DIR, "files", "raw", "_staging")

CHROME_CANDIDATES = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
)


def get_staging_dir():
    """Carpeta única de descarga para toda la sesión (varios reportes comparten Chrome)."""
    os.makedirs(STAGING_DIR, exist_ok=True)
    return STAGING_DIR


def _chrome_binary():
    for path in CHROME_CANDIDATES:
        if path and os.path.isfile(path):
            return path
    return None


def create_chrome_driver(download_dir=None):
    """Abre Chrome con Selenium Manager (incluido en Selenium 4.6+)."""
    staging_dir = get_staging_dir()
    os.makedirs(staging_dir, exist_ok=True)
    options = webdriver.ChromeOptions()

    binary = _chrome_binary()
    if binary:
        options.binary_location = binary
        print(f"Chrome: {binary}", flush=True)
    else:
        print("Chrome: usando el del PATH", flush=True)

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--remote-allow-origins=*")
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option(
        "prefs",
        {
            "download.default_directory": os.path.abspath(staging_dir),
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        },
    )

    print("Abriendo Chrome (Selenium Manager)...", flush=True)
    start = time.time()
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(90)
    driver.set_script_timeout(60)
    print(f"Chrome abierto en {time.time() - start:.1f}s (descargas -> {staging_dir})", flush=True)

    try:
        stealth(
            driver,
            languages=["es-AR", "es"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
    except Exception as exc:
        print(f"stealth omitido: {exc}", flush=True)

    return driver
