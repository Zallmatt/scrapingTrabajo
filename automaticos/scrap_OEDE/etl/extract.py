"""
EXTRACT - Módulo de extracción de datos OEDE
Responsabilidad: Descargar el Excel de remuneraciones por sector desde argentina.gob.ar
"""
import os
import logging
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from unidecode import unidecode
from urllib3 import disable_warnings

disable_warnings()

logger = logging.getLogger(__name__)

FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files')
NOMBRE_ARCHIVO = 'ev_remun_trab_reg_por_sector.xlsx'
URL = 'https://www.argentina.gob.ar/trabajo/estadisticas/oede-estadisticas-provinciales'
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
}


class ExtractOEDE:
    """Descarga el Excel de remuneraciones provinciales (serie mensual a 2 dígitos)."""

    def extract(self) -> str:
        os.makedirs(FILES_DIR, exist_ok=True)
        logger.info("[EXTRACT] Navegando a %s", URL)
        resp = requests.get(URL, headers=HEADERS, verify=False, timeout=60)
        resp.raise_for_status()

        href = self._elegir_link(resp.text)
        url_archivo = urljoin(URL, href)
        logger.info("[EXTRACT] URL del archivo: %s", url_archivo)

        ruta = os.path.join(FILES_DIR, NOMBRE_ARCHIVO)
        archivo = requests.get(url_archivo, headers=HEADERS, verify=False, timeout=120)
        archivo.raise_for_status()
        with open(ruta, 'wb') as f:
            f.write(archivo.content)
        logger.info("[EXTRACT] Archivo guardado en: %s (%d bytes)", ruta, len(archivo.content))
        return ruta

    @staticmethod
    def _elegir_link(html: str) -> str:
        """
        El XPath fijo apuntaba a la 1ª tabla (empleo). Buscamos por texto:
        remuneraciones + sector + mensual + 2 dígitos.
        """
        soup = BeautifulSoup(html, 'html.parser')
        candidatos = []
        for a in soup.select('a[href]'):
            href = a.get('href') or ''
            if not href.lower().endswith(('.xlsx', '.xls')):
                continue
            tr = a.find_parent('tr')
            texto = unidecode((tr.get_text(' ', strip=True) if tr else a.get_text(' ', strip=True)).lower())
            if 'remuneracion' not in texto or 'sector' not in texto:
                continue
            if 'anual' in texto:
                continue
            score = 0
            if 'mensual' in texto:
                score += 4
            if 'trimestral' in texto:
                score += 2
            if 'dos digit' in texto or '2 digit' in texto or '2dig' in texto:
                score += 3
            candidatos.append((score, href, texto[:160]))

        if not candidatos:
            raise RuntimeError(
                "[EXTRACT] No se encontró el Excel de remuneraciones por sector en la página OEDE."
            )

        candidatos.sort(key=lambda x: x[0], reverse=True)
        elegido = candidatos[0]
        logger.info("[EXTRACT] Link elegido (score=%s): %s", elegido[0], elegido[2])
        return elegido[1]
