"""
EXTRACT - Módulo de extracción de datos CBT/CBA
Responsabilidad: Descargar el XLS de Canasta Básica desde INDEC usando Selenium
"""
import os
import logging
import re
import requests
import urllib3
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

# Configuración de rutas y URL
FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files', 'data')
NOMBRE_ARCHIVO = 'CBT.xls'
URL = 'https://www.indec.gob.ar/indec/web/Nivel4-Tema-4-43-149'
# Full XPath proporcionado por el usuario
XPATH_LINK = "/html/body/div[2]/div[1]/div[2]/div[3]/div[2]/div[2]/div/div[2]/div/div[2]/div/div[2]/div/div/a"

MESES_MAP = {
    'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'ago': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dic': 12
}

class ExtractorCBT:
    """Descarga el XLS de la serie de CBA y CBT desde INDEC y obtiene la fecha de publicación."""

    def descargar_archivo(self) -> tuple:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        os.makedirs(FILES_DIR, exist_ok=True)
        logger.info("[EXTRACT CBT] Iniciando descarga de archivo de Canasta Básica desde INDEC.")
        
        driver = self._crear_driver()
        href = None
        link_text = ""
        try:
            logger.info("[EXTRACT CBT] Navegando a la URL de INDEC: %s", URL)
            driver.get(URL)
            
            # Espera larga de 30 segundos por si el sitio está lento
            wait = WebDriverWait(driver, 30)
            
            # Buscamos el link usando el Full XPath
            link_element = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_LINK)))
            href = link_element.get_attribute('href')
            link_text = link_element.get_attribute('textContent') or link_element.text
            logger.info("[EXTRACT CBT] URL del archivo XLS encontrada: %s", href)
            logger.info("[EXTRACT CBT] Texto del enlace para parsear fecha: '%s'", link_text)
            
        except Exception as e:
            logger.error("[EXTRACT CBT] Error al buscar el enlace de descarga en la página: %s", e)
            raise e
        finally:
            driver.quit()

        # Parsear fecha de publicación del INDEC
        fecha_publicacion = self._parse_indec_latest_date(link_text)
        logger.info("[EXTRACT CBT] Fecha de publicación INDEC extraída: %s", fecha_publicacion)

        # Descarga mediante requests
        ruta = os.path.join(FILES_DIR, NOMBRE_ARCHIVO)
        logger.info("[EXTRACT CBT] Descargando archivo XLS...")
        response = requests.get(href, verify=False, timeout=60)
        response.raise_for_status()
        
        with open(ruta, 'wb') as f:
            f.write(response.content)
            
        logger.info("[EXTRACT CBT] Archivo XLS guardado exitosamente en: %s", ruta)
        return ruta, fecha_publicacion

    @staticmethod
    def _parse_indec_latest_date(text):
        if not text:
            return None
        # Buscamos la frase "a [mes] de [año]" al final del texto del enlace
        match = re.search(r'a\s+([a-zñáéíóú]+)\s+de\s+(\d{4})', text.lower())
        if match:
            mes_str = match.group(1)[:3]
            anio = int(match.group(2))
            mes = MESES_MAP.get(mes_str)
            if mes:
                try:
                    return pd.to_datetime(f"{anio}-{mes:02d}-01")
                except Exception:
                    pass
        return None

    @staticmethod
    def _crear_driver():
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        driver = webdriver.Chrome(options=options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        })
        return driver
