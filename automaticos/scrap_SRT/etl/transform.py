"""
TRANSFORM - Módulo de transformación de datos SRT
Responsabilidad: Procesar los CSVs del SRT y generar el DataFrame consolidado
"""
import os
import csv
import logging
import pandas as pd

logger = logging.getLogger(__name__)

FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'files')

DICT_PROVINCIAS = {
    'C.A.B.A.': 2, 'Buenos Aires': 6, 'Catamarca': 10, 'Chaco': 22,
    'Chubut': 26, 'Cordoba': 14, 'Corrientes': 18, 'Entre Rios': 30,
    'Formosa': 34, 'Jujuy': 38, 'La Pampa': 42, 'La Rioja': 46,
    'Mendoza': 50, 'Misiones': 54, 'Neuquen': 58, 'Rio Negro': 62,
    'Salta': 66, 'San Juan': 70, 'San Luis': 74, 'Santa Cruz': 78,
    'Santa Fe': 82, 'Santiago del Estero': 86, 'Sin datos': 0,
    'Tierra del Fuego': 94, 'Tucuman': 90,
}

COLUMNAS = ['periodo', 'jurisdiccion_desc', 'seccion', 'grupo', 'ciiu',
            'cant_personas_trabaj_cp', 'cant_personas_trabaj_up', 'remuneracion']


class TransformSRT:
    """Transforma los CSVs del SRT en un DataFrame consolidado."""

    def transform(self, files_dir: str = None) -> pd.DataFrame:
        if files_dir is None:
            files_dir = FILES_DIR

        archivos = [f for f in os.listdir(files_dir) if f.endswith('.csv')]
        logger.info("[TRANSFORM] Procesando %d archivos CSV...", len(archivos))

        dfs = []
        for archivo in archivos:
            ruta = os.path.join(files_dir, archivo)
            logger.info("[TRANSFORM] Procesando: %s", archivo)
            self._normalizar_csv(ruta)
            df = self._crear_df(ruta)
            if df is not None and not df.empty:
                dfs.append(df)
            else:
                logger.warning("[TRANSFORM] %s omitido (vacío o con error).", archivo)

        if not dfs:
            raise ValueError("[TRANSFORM] Ningún CSV generó datos válidos.")

        df_final = pd.concat(dfs, ignore_index=True)
        logger.info("[TRANSFORM] DataFrame final: %d filas", len(df_final))
        return df_final

    def _normalizar_csv(self, ruta: str):
        sep = self._detectar_separador(ruta)
        try:
            df = pd.read_csv(ruta, sep=sep, engine='python', dtype=str)
            df.to_csv(ruta, index=False, sep=',', quoting=csv.QUOTE_MINIMAL, encoding='utf-8')
        except Exception as e:
            logger.warning("[TRANSFORM] Error normalizando %s: %s", ruta, e)

    def _crear_df(self, ruta: str) -> pd.DataFrame:
        try:
            df = pd.read_csv(ruta)
            df.columns = df.columns.str.strip().str.lower()
            df = df[COLUMNAS].copy()

            # Tipos de datos
            df[['periodo', 'jurisdiccion_desc', 'seccion', 'ciiu']] = \
                df[['periodo', 'jurisdiccion_desc', 'seccion', 'ciiu']].astype(str)

            # Normalización robusta de números (para cualquier período)
            df['remuneracion'] = df['remuneracion'].astype(str).str.strip()
            df['remuneracion'] = (df['remuneracion']
                                  .str.replace('.', '', regex=False)
                                  .str.replace(',', '.', regex=False))
            df['remuneracion'] = pd.to_numeric(df['remuneracion'], errors='coerce').fillna(0)
            
            df['cant_personas_trabaj_up'] = pd.to_numeric(df['cant_personas_trabaj_up'], errors='coerce').fillna(0)
            df['cant_personas_trabaj_cp'] = pd.to_numeric(df['cant_personas_trabaj_cp'], errors='coerce').fillna(0)

            # Fecha
            df['año'] = df['periodo'].str[:4].astype(int)
            df['mes'] = df['periodo'].str[4:6].astype(int)
            df['fecha'] = pd.to_datetime(df[['año', 'mes']].rename(columns={'año': 'year', 'mes': 'month'}).assign(day=1))
            df = df.drop(columns=['año', 'mes', 'periodo'])

            # Agrupar
            df_agr = df.groupby(
                ['fecha', 'jurisdiccion_desc', 'seccion', 'grupo', 'ciiu'], as_index=False
            ).agg({
                'cant_personas_trabaj_cp': 'sum',
                'cant_personas_trabaj_up': 'sum',
                'remuneracion': 'sum'
            })

            df_agr['cant_personas_trabaj_up'] += df_agr['cant_personas_trabaj_cp']
            df_agr.drop(columns=['cant_personas_trabaj_cp'], inplace=True)
            
            # Cálculo de salario
            df_agr['salario'] = (df_agr['remuneracion'] / df_agr['cant_personas_trabaj_up'].replace(0, float('nan'))).fillna(0)

            # Provincias
            df_agr['jurisdiccion_desc'] = df_agr['jurisdiccion_desc'].replace(DICT_PROVINCIAS)
            df_agr = df_agr.rename(columns={
                'jurisdiccion_desc': 'id_provincia',
                'seccion': 'id_seccion',
                'ciiu': 'id_ciiu',
                'grupo': 'id_grupo'
            })
            df_agr['id_provincia'] = pd.to_numeric(df_agr['id_provincia'], errors='coerce').fillna(0).astype(int)

            float_cols = df_agr.select_dtypes(include='float').columns
            df_agr[float_cols] = df_agr[float_cols].round(2)

            return df_agr
        except Exception as e:
            logger.error("[TRANSFORM] Error procesando %s: %s", ruta, e)
            return None

    @staticmethod
    def _detectar_separador(ruta: str) -> str:
        with open(ruta, 'r', newline='', encoding='utf-8') as f:
            primera = f.readline()
        if ',' in primera and ';' in primera:
            return ';'
        return ',' if ',' in primera else ';'