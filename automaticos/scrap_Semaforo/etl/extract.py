"""
EXTRACT - Módulo de extracción de datos Semáforo
Responsabilidad: Leer datos desde Google Sheets (interanual e intermensual)
"""
import os
import logging
from json import loads
from pandas import DataFrame
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

SPREADSHEET_ID = '1L_EzJNED7MdmXw_rarjhhX8DpL7HtaKpJoRwyxhxHGI'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

COLUMNAS_SEMAFORO = [
    'fecha',
    'combustible_vendido',
    'patentamiento_0km_auto',
    'patentamiento_0km_motocicleta',
    'pasajeros_salidos_terminal_corrientes',
    'pasajeros_aeropuerto_corrientes',
    'venta_supermercados_autoservicios_mayoristas',
    'exportaciones_aduana_corrientes_dolares',
    'exportaciones_aduana_corrientes_toneladas',
    'empleo_privado_registrado_sipa',
    'permisos_edificacion_unidades',
    'permisos_edificacion_m2'
]


class ExtractSemaforo:
    """Extrae datos del Semáforo desde Google Sheets."""

    def __init__(self):
        key_dict = loads(os.getenv('GOOGLE_SHEETS_API_KEY'))
        creds = service_account.Credentials.from_service_account_info(key_dict, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        self.sheet = service.spreadsheets()

    def extract(self):
        """
        Extrae ambas hojas (interanual e intermensual) leyendo hasta la fila 14 (fila 13 incluida).
        """
        logger.info("[EXTRACT] Leyendo hoja interanual...")
        df_interanual = self._leer_hoja('Semaforo!B2:14')
        logger.info("[EXTRACT] Leyendo hoja intermensual...")
        df_intermensual = self._leer_hoja('Semaforo Intermensual!B2:14')
        return df_interanual, df_intermensual

    def _leer_hoja(self, rango: str) -> DataFrame:
        """Lee una hoja de Google Sheets y devuelve un DataFrame crudo."""
        result = self.sheet.values().get(
            spreadsheetId=SPREADSHEET_ID, range=rango
        ).execute()

        filas = result.get('values', [])
        if not filas:
            raise ValueError(f"No se obtuvieron datos del rango '{rango}'")

        # Primera fila: fechas; resto: indicadores
        fechas = filas[0]
        filas_indicadores = filas[1:]

        max_length = max(len(f) for f in filas_indicadores) if filas_indicadores else 0
        
        # Rellenamos nulos en horizontal
        filas_indicadores = self._rellenar_nulos(filas_indicadores, max_length)
        fechas_truncadas = fechas[:max_length]

        df = DataFrame()
        df['fecha'] = fechas_truncadas
        for i, col in enumerate(COLUMNAS_SEMAFORO[1:]):
            if i < len(filas_indicadores):
                df[col] = filas_indicadores[i]
            else:
                df[col] = [None] * len(fechas_truncadas)
                logger.warning(f"[EXTRACT] Indicador '{col}' no encontrado en el Sheets. Rellenando con nulos.")

        logger.info("[EXTRACT] Hoja '%s' leída con %d columnas y %d periodos.", rango, len(df.columns), len(df))
        return df

    @staticmethod
    def _rellenar_nulos(filas: list, max_length: int) -> list:
        return [fila + [None] * (max_length - len(fila)) for fila in filas]