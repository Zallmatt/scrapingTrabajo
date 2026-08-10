"""
EXTRACT - Módulo de extracción de datos VentasCombustible
Responsabilidad: Descargar el CSV de ventas de combustible desde datos.gob.ar usando BeautifulSoup
"""
import os
import logging
import requests
import time
from bs4 import BeautifulSoup
import urllib3

logger = logging.getLogger(__name__)

# Desactivar advertencias de SSL no verificado (el sitio de energía a veces tiene problemas de certificados)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files')
URL = 'http://datos.energia.gob.ar/dataset/refinacion-y-comercializacion-de-petroleo-gas-y-derivados-tablas-dinamicas/archivo/f0e4e10a-e4b8-44e6-bd16-763a43742107'
NOMBRE_ARCHIVO = 'ventas_combustible.csv'


class ExtractVentasCombustible:
    """Descarga el CSV de ventas de combustible."""

    def extract(self) -> str:
        os.makedirs(FILES_DIR, exist_ok=True)
        ruta = os.path.join(FILES_DIR, NOMBRE_ARCHIVO)

        # --- Verificación de frescura del archivo ---
        if os.path.exists(ruta):
            tiempo_archivo = os.path.getmtime(ruta)
            # 3600 segundos = 1 hora
            if (time.time() - tiempo_archivo) < 3600:
                logger.info("[EXTRACT] Usando archivo existente (descargado hace menos de 1 hora).")
                return ruta
        # ----------------------------------------------------
        
        # 1. Obtener URL de descarga usando BeautifulSoup
        logger.info("[EXTRACT] Navegando a %s", URL)
        try:
            r_page = requests.get(URL, timeout=30, verify=False)
            r_page.raise_for_status()
            soup = BeautifulSoup(r_page.content, 'html.parser')
            
            # Buscar el enlace de descarga
            elem = soup.find('a', class_='btn-green')
            if not elem:
                # Intento alternativo buscando por href
                for a in soup.find_all('a', href=True):
                    if 'download/ventas-excluye-ventas-a-empresas-del-sector' in a['href']:
                        elem = a
                        break
            
            if not elem:
                raise ValueError("No se pudo encontrar el enlace de descarga en la página.")
                
            url_archivo = elem['href']
            logger.info("[EXTRACT] URL del CSV encontrada: %s", url_archivo)
        except Exception as e:
            logger.error("[EXTRACT] Error al extraer la URL del CSV: %s", e)
            raise

        # 2. Descarga por Streaming con Reintentos
        max_reintentos = 3
        for i in range(max_reintentos):
            try:
                logger.info(f"[EXTRACT] Intentando descarga (Intento {i+1})...")
                with requests.get(url_archivo, stream=True, timeout=300, verify=False) as r:
                    r.raise_for_status()
                    with open(ruta, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                logger.info("[EXTRACT] Descarga completada.")
                return ruta
            except requests.exceptions.RequestException as e:
                logger.warning(f"[EXTRACT] Fallo en intento {i+1}: {e}")
                time.sleep(5)
                if i == max_reintentos - 1:
                    raise

