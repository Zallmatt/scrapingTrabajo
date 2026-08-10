"""
LOAD - Módulo de carga de datos DNRPA
Responsabilidad: Cargar datos a PostgreSQL y actualizar Google Sheets (Fila 7 y 8)
"""
import os
import logging
import pandas as pd
from sqlalchemy import create_engine, text
from google.oauth2 import service_account
from googleapiclient.discovery import build
from json import loads

logger = logging.getLogger(__name__)

class LoadDNRPA:
    def __init__(self, host, user, password, database, port=None, version="2"):
        self.host, self.user, self.password, self.database = host, user, password, database
        self.port = port or (5432 if version == "2" else 3306)
        self.version = version  # "1": MySQL, "2": PostgreSQL
        self.engine = None

    def _conectar(self):
        if not self.engine:
            if self.version == "2": # PostgreSQL
                url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            else: # MySQL
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
            self.engine = create_engine(url)

    def load(self, df: pd.DataFrame):
        try:
            self._conectar()
            schema = self._get_schema()
            table_name = "dnrpa"

            # Si estamos en Postgres, usamos el nombre calificado schema.table
            full_table_name = f"{schema}.{table_name}" if schema else table_name

            logger.info("--- Iniciando carga para: DATOS DNRPA (Tabla: %s) ---", table_name)

            if df is None or df.empty:
                logger.info("[LOAD] DataFrame vacío. Omitiendo carga.")
                return

            # Obtener info de la BDD para logging (fecha máxima general)
            try:
                with self.engine.connect() as conn:
                    fecha_max_db = conn.execute(text(f"SELECT MAX(fecha) FROM {full_table_name}")).scalar()
            except Exception:
                fecha_max_db = None

            df['fecha'] = pd.to_datetime(df['fecha'])
            fecha_max_extract = df['fecha'].max()

            fecha_db_str = fecha_max_db.strftime('%Y-%m-%d') if hasattr(fecha_max_db, 'strftime') else 'Ninguna (Tabla vacía)'
            fecha_ext_str = fecha_max_extract.strftime('%Y-%m-%d') if hasattr(fecha_max_extract, 'strftime') else 'Ninguna (DF vacío)'
            
            logger.info(f"[LOAD] Comparación de fechas -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")

            # 2. Verificar si hay cambios en el último año
            ultimo_anio = int(df['fecha'].dt.year.max())
            df_anio = df[df['fecha'].dt.year == ultimo_anio]
            
            # SQL genérico usando EXTRACT (funciona en ambos motores)
            query_count = text(f"SELECT COUNT(*) FROM {full_table_name} WHERE EXTRACT(YEAR FROM fecha) = :anio")
            query_delete = text(f"DELETE FROM {full_table_name} WHERE EXTRACT(YEAR FROM fecha) = :anio")

            with self.engine.begin() as conn:
                # 1. Verificar registros existentes
                try:
                    count_bd = conn.execute(query_count, {"anio": ultimo_anio}).scalar()
                except Exception:
                    count_bd = 0 # En caso de que la tabla aún no exista

                logger.info(f"[LOAD] Comparación para el año {ultimo_anio} -> Base: {count_bd} registros | Extraído: {len(df_anio)} registros")

                if count_bd == len(df_anio):
                    logger.info(f"[LOAD] No hay datos nuevos para {ultimo_anio}. La base está al día. No se sube a la base.")
                    return

                # 2. Recargar año actual
                logger.info(f"[LOAD] ¡Datos nuevos detectados! Refrescando/insertando datos para el año {ultimo_anio}. Se subirán {len(df_anio)} registros.")
                conn.execute(query_delete, {"anio": ultimo_anio})
                df_anio.to_sql(table_name, con=conn, schema=schema, if_exists='append', index=False)
                try:
                    alter_query = f"ALTER TABLE {full_table_name} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table_name} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    conn.execute(text(alter_query))
                except Exception as e:
                    logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")
            
            logger.info("[OK] Carga a la base completada.")

            # 3. Actualizar Sheets
            logger.info("[LOAD] Iniciando actualización de Google Sheets...")
            self._update_sheets(df_anio)
            logger.info("[OK] Carga y actualización de Sheets completada.")

        except Exception as e:
            logger.error(f"Error en Load DNRPA: {e}")
            raise

    def _get_schema(self):
        """Devuelve 'public' solo si estamos en PostgreSQL (v2)"""
        return "public" if self.version == "2" else None

    def _update_sheets(self, df):
        """Actualiza Datos de Corrientes y Matrices de NEA + Nación (Autos y Motos)"""
        try:
            # 1. Identificar última fecha y preparar tags
            ultima_fecha = df['fecha'].max()
            meses_es = {1:"ene", 2:"feb", 3:"mar", 4:"abr", 5:"may", 6:"jun", 7:"jul", 8:"ago", 9:"sept", 10:"oct", 11:"nov", 12:"dic"}
            tag_fecha_datos = f"{meses_es[ultima_fecha.month]}-{str(ultima_fecha.year)[-2:]}" # "mar-26"
            tag_fecha_matriz = f"{meses_es[ultima_fecha.month]}-{ultima_fecha.year}"      # "mar-2026"

            # 2. Filtrar datos necesarios (Corrientes, NEA y Nación)
            df_mes = df[df['fecha'] == ultima_fecha]
            
            map_filas_matriz = {
                22: 2,  # 22 es CHACO (Fila 2 en la matriz de Sheets)
                54: 3,  # 54 es MISIONES (Fila 3)
                34: 4,  # 34 es FORMOSA (Fila 4)
                1: 5    # 1 es NACION/TOTAL (Fila 5)
            }

            # 3. Preparar conexión a Google Sheets
            key_dict = loads(os.getenv('GOOGLE_SHEETS_API_KEY'))
            SPREADSHEET_ID = '1L_EzJNED7MdmXw_rarjhhX8DpL7HtaKpJoRwyxhxHGI'
            creds = service_account.Credentials.from_service_account_info(key_dict, scopes=['https://www.googleapis.com/auth/spreadsheets'])
            service = build('sheets', 'v4', credentials=creds)

            batch_data = []

            # --- A. ACTUALIZAR HOJA "DATOS" (Corrientes Fila 7 y 8) ---
            res_datos = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range="Datos!3:3").execute()
            headers_datos = res_datos.get("values", [[]])[0]
            col_datos_idx = next((i for i, h in enumerate(headers_datos) if h and tag_fecha_datos in h.lower()), None)

            if col_datos_idx is not None:
                letra_datos = self._num_to_col(col_datos_idx)
                val_autos_ctes = df_mes[(df_mes['id_provincia'] == 18) & (df_mes['id_vehiculo'] == 1)]['cantidad'].sum()
                val_motos_ctes = df_mes[(df_mes['id_provincia'] == 18) & (df_mes['id_vehiculo'] == 2)]['cantidad'].sum()
                batch_data.append({'range': f"Datos!{letra_datos}7", 'values': [[str(val_autos_ctes)]]})
                batch_data.append({'range': f"Datos!{letra_datos}8", 'values': [[str(val_motos_ctes)]]})

            # --- B. ACTUALIZAR MATRICES NEA + NACIÓN ---
            # Procesamos Hoja "Patentamiento Autos" (id_vehiculo 1) y "Patentamiento Motos" (id_vehiculo 2)
            for hoja, vehiculo_id in [("Patentamiento Autos", 1), ("Patentamiento Motos", 2)]:
                res_matriz = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range=f"'{hoja}'!1:1").execute()
                headers_matriz = res_matriz.get("values", [[]])[0]
                col_matriz_idx = next((i for i, h in enumerate(headers_matriz) if h and tag_fecha_matriz in h.lower()), None)

                if col_matriz_idx is not None:
                    letra_matriz = self._num_to_col(col_matriz_idx)
                    for prov_id, fila in map_filas_matriz.items():
                        valor = df_mes[(df_mes['id_provincia'] == prov_id) & (df_mes['id_vehiculo'] == vehiculo_id)]['cantidad'].sum()
                        batch_data.append({
                            'range': f"'{hoja}'!{letra_matriz}{fila}",
                            'values': [[str(int(valor))]]
                        })

            # 4. Ejecutar toda la actualización en un solo viaje
            if batch_data:
                service.spreadsheets().values().batchUpdate(
                    spreadsheetId=SPREADSHEET_ID, 
                    body={'valueInputOption': 'USER_ENTERED', 'data': batch_data}
                ).execute()
                logger.info(f"[OK] Sheets actualizado para {tag_fecha_matriz} (Corrientes, NEA y Nación)")

        except Exception as e:
            logger.error(f"Error actualizando Sheets DNRPA: {e}")

    def _num_to_col(self, n):
        res = ""
        while n >= 0:
            res = chr(n % 26 + 65) + res
            n = n // 26 - 1
        return res

    def close(self):
        if self.engine:
            self.engine.dispose()