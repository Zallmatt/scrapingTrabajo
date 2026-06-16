"""
Transformer para procesar datos de CBA y CBT.

En este script cargamos las canastas de GBA (individual y familias) de CBT.xls
y extraemos datos del NEA desde una planilla de Google Sheets del equipo.
"""
import os
import logging
import json
import re
import pandas as pd
import numpy as np
from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger(__name__)

class TransformerCBTCBA:
    """
    Procesa los archivos descargados de GBA y los une con los datos de NEA de Google Sheets.
    """

    def __init__(self):
        # Centralizamos la configuración de rutas
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.base_dir, 'files', 'data')
        self.file_cbt = os.path.join(self.data_dir, 'CBT.xls')
        self.spreadsheet_id = "17K0k_OvXFa-9jjIaX7Q5Nwz5TkxHMqXIxm-qYhDWYyA"
        self.sheet_name = "CBA y CBT mensual"

    @staticmethod
    def _clean_numeric(val):
        if pd.isna(val) or val is None:
            return np.nan
        if isinstance(val, (int, float)):
            return float(val)
        val_str = str(val).strip()
        if val_str == '' or val_str == '$0' or val_str == '0' or val_str == '$0,00' or val_str == '-':
            return np.nan
        val_str = val_str.replace('$', '').replace(' ', '')
        val_str = val_str.replace('.', '').replace(',', '.')
        try:
            return float(val_str)
        except ValueError:
            return np.nan

    @staticmethod
    def _parse_fecha(val):
        if pd.isna(val) or val is None:
            return pd.NaT
        val_str = str(val).strip().lower()
        if not val_str:
            return pd.NaT
            
        # Match MM/YY format (e.g. 04/16)
        if re.match(r'^\d{2}/\d{2}$', val_str):
            try:
                return pd.to_datetime(val_str, format='%m/%y')
            except Exception:
                return pd.NaT
                
        # Match mmm-YY or mmmm-YY format (e.g. dic-16, sept-24, ene-26)
        meses_map = {
            'ene': 1, 'feb': 2, 'mar': 3, 'abr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'ago': 8, 'sep': 9, 'sept': 9, 'oct': 10, 'nov': 11, 'dic': 12
        }
        match = re.match(r'^([a-z]{3,4})-(\d{2})$', val_str)
        if match:
            mes_str, anio_str = match.groups()
            mes = meses_map.get(mes_str)
            if mes:
                anio = 2000 + int(anio_str)
                return pd.to_datetime(f"{anio}-{mes:02d}-01")
                
        # Fallback
        try:
            return pd.to_datetime(val_str)
        except Exception:
            return pd.NaT

    def extraer_datos_nea(self, fecha_limite) -> pd.DataFrame:
        """Extrae datos del NEA desde la planilla de Google Sheets."""
        logger.info("[TRANSFORM CBT] Iniciando extracción de datos NEA desde Google Sheets.")
        key_env = os.getenv('GOOGLE_SHEETS_API_KEY')
        if not key_env:
            logger.error("[TRANSFORM CBT] Variable de entorno GOOGLE_SHEETS_API_KEY no encontrada.")
            raise ValueError("GOOGLE_SHEETS_API_KEY no encontrada en variables de entorno.")

        try:
            key_dict = json.loads(key_env)
            scopes = ['https://www.googleapis.com/auth/spreadsheets']
            creds = service_account.Credentials.from_service_account_info(key_dict, scopes=scopes)
            service = build('sheets', 'v4', credentials=creds)
            
            rango = f"'{self.sheet_name}'!A:Z"
            result = service.spreadsheets().values().get(spreadsheetId=self.spreadsheet_id, range=rango).execute()
            values = result.get('values', [])
            
            if not values:
                logger.warning("[TRANSFORM CBT] No se encontraron datos en la planilla de Google Sheets '%s'.", self.sheet_name)
                return pd.DataFrame(columns=['fecha', 'cba_nea', 'cbt_nea'])
                
            header = values[0]
            data = values[1:]
            
            clean_data = []
            for row in data:
                if len(row) < len(header):
                    row = row + [None] * (len(header) - len(row))
                elif len(row) > len(header):
                    row = row[:len(header)]
                clean_data.append(row)
                
            df_sheet = pd.DataFrame(clean_data, columns=header)
            
            df_sheet['fecha'] = df_sheet['Fecha'].apply(self._parse_fecha)
            df_sheet['cba_nea'] = df_sheet['CBA NEA'].apply(self._clean_numeric)
            df_sheet['cbt_nea'] = df_sheet['CBT NEA'].apply(self._clean_numeric)
            
            df_nea = df_sheet[['fecha', 'cba_nea', 'cbt_nea']].dropna(subset=['fecha']).reset_index(drop=True)
            
            # Filtrar hasta la fecha limite de INDEC si está provista
            if fecha_limite is not None:
                fecha_limite = pd.to_datetime(fecha_limite)
                df_nea = df_nea[df_nea['fecha'] <= fecha_limite]
                
            df_nea = df_nea.dropna(subset=['cba_nea', 'cbt_nea'], how='all').reset_index(drop=True)
            logger.info("[TRANSFORM CBT] Datos de NEA extraídos y filtrados con éxito: %d filas.", len(df_nea))
            return df_nea

        except Exception as e:
            logger.error("[TRANSFORM CBT] Error al leer datos de Google Sheet (NEA): %s", e)
            raise e

    def transform_datalake(self, fecha_indec=None) -> pd.DataFrame:
        """Coordina la transformación completa uniendo GBA de CBT.xls y NEA de Google Sheets."""
        logger.info("[TRANSFORM CBT] Iniciando transformación de datos GBA (XLS) y NEA (Sheets).")

        # 1. Procesar Hoja 1 (Adultos - GBA)
        logger.info("[TRANSFORM CBT] Procesando datos de GBA desde el archivo: %s", self.file_cbt)
        df_adultos = pd.read_excel(self.file_cbt, sheet_name=0, usecols=[0, 1, 3], skiprows=6, skipfooter=1)
        df_adultos.columns = ['fecha', 'cba_adulto', 'cbt_adulto']
        
        # Limpieza de valores
        for col in ['cba_adulto', 'cbt_adulto']:
            df_adultos[col] = pd.to_numeric(df_adultos[col].astype(str).str.replace(',', ''), errors='coerce')

        # Corrección de outliers conocidos
        mask_cba = df_adultos['cba_adulto'] == 13874431
        df_adultos.loc[mask_cba, 'cba_adulto'] = 138744.31
        mask_cbt = df_adultos['cbt_adulto'] == 31217470
        df_adultos.loc[mask_cbt, 'cbt_adulto'] = 312174.70

        # 2. Procesar Hoja 2 (Hogares - GBA)
        df_hogares = pd.read_excel(self.file_cbt, sheet_name=3, usecols=[2, 6], skiprows=6, skipfooter=1)
        df_hogares.columns = ['cba_hogar', 'cbt_hogar']

        # 3. Limpieza de filas vacías
        df_adultos = df_adultos.dropna(subset=['fecha']).reset_index(drop=True)
        df_hogares = df_hogares.dropna(how='all').reset_index(drop=True)

        # 4. Concatenar bases de CBT.xls (Aseguramos mismo largo para GBA)
        df_base = pd.concat([df_adultos, df_hogares], axis=1)
        df_base['fecha'] = pd.to_datetime(df_base['fecha'])

        # 5. Obtener fecha de corte
        if fecha_indec is None:
            fecha_indec = df_base['fecha'].max()
            logger.info("[TRANSFORM CBT] Fecha de corte no provista. Usando fecha máxima de CBT.xls: %s", fecha_indec)
        else:
            fecha_indec = pd.to_datetime(fecha_indec)
            logger.info("[TRANSFORM CBT] Usando fecha de corte de INDEC: %s", fecha_indec)

        # Truncar df_base si es necesario para no pasarse de la fecha publicada de INDEC
        df_base = df_base[df_base['fecha'] <= fecha_indec].reset_index(drop=True)

        # 6. Extraer datos del NEA desde Google Sheets
        df_nea = self.extraer_datos_nea(fecha_indec)

        # 7. Unir GBA y NEA por la columna fecha (evita bugs de desalineación)
        df_final = pd.merge(df_base, df_nea, on='fecha', how='left')

        logger.info("[TRANSFORM CBT] Transformación completada. DataFrame final con %d registros.", len(df_final))
        return df_final
