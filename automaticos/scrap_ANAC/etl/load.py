"""
LOAD - Módulo de carga de datos ANAC
Responsabilidad: Cargar datos a PostgreSQL y actualizar Google Sheets
"""
import os
import logging
import pandas as pd
import psycopg2
import pymysql  # Necesario para la base vieja si es MySQL
from sqlalchemy import create_engine, text
from google.oauth2 import service_account
from googleapiclient.discovery import build
from json import loads

logger = logging.getLogger(__name__)

class LoadANAC:
    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.version = str(version)
        self.conn = None
        self.engine = None
        self.cursor = None

    def conectar_bdd(self):
        if not self.conn:
            try:
                if self.version == "1":
                    puerto_mysql = int(self.port) if self.port else 3306
                    self.conn = pymysql.connect(
                        host=self.host, user=self.user, password=self.password,
                        database=self.database, port=puerto_mysql
                    )
                    conn_str = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{puerto_mysql}/{self.database}"
                    logger.info(f"[LOAD ANAC] Conexión establecida a MySQL (v1) en {self.host}")
                else:
                    puerto_pg = self.port if self.port else 5432
                    self.conn = psycopg2.connect(
                        host=self.host, user=self.user, password=self.password,
                        database=self.database, port=puerto_pg
                    )
                    conn_str = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{puerto_pg}/{self.database}"
                    logger.info(f"[LOAD ANAC] Conexión establecida a PostgreSQL (v2) en {self.host}")

                self.engine = create_engine(conn_str)
                self.cursor = self.conn.cursor()
            except Exception as err:
                logger.error(f"[LOAD ANAC] Error al conectar a la BD v{self.version}: {err}")
                raise
        return self
    
    def _get_schema_prefix(self):
        """Retorna el prefijo de esquema solo si es Postgres."""
        return "public." if self.version == "2" else ""

    def load_to_database(self, df):
        self.conectar_bdd()
        df = df[['fecha', 'aeropuerto', 'cantidad']].copy()
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
        
        prefix = self._get_schema_prefix()
        tabla_completa = f"{prefix}anac"
        
        try:
            fecha_min = df['fecha'].min()
            fecha_max = df['fecha'].max()
            
            # 1. Borrado eficiente (SQLAlchemy maneja el prefijo según el motor)
            sql_delete = text(f"DELETE FROM {tabla_completa} WHERE fecha BETWEEN :fmin AND :fmax")
            with self.engine.begin() as conn:
                conn.execute(sql_delete, {"fmin": fecha_min, "fmax": fecha_max})
                # 2. Inserción (Usamos solo el nombre de la tabla sin prefijo para to_sql si pasamos el schema aparte)
                # En MySQL el schema es None, en Postgres es 'public'
                schema_name = "public" if self.version == "2" else None
                df.to_sql(name='anac', con=conn, schema=schema_name, if_exists='append', index=False, method='multi')
                try:
                    alter_query = f"ALTER TABLE {tabla_completa} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {tabla_completa} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    conn.execute(text(alter_query))
                except Exception as e:
                    logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")
            
            logger.info(f"[LOAD] v{self.version} OK: {len(df)} filas cargadas.")
        except Exception as e:
            logger.error(f"[LOAD ERROR] v{self.version}: {e}")
            raise

    def cerrar_conexion(self):
        """Cierra las conexiones"""
        try:
            if self.cursor: self.cursor.close()
            if self.conn: self.conn.close()
            if self.engine: self.engine.dispose()
            self.conn = self.cursor = self.engine = None
            logger.info("Conexión a BD cerrada")
        except Exception as e:
            logger.warning(f"Error al cerrar conexión: {e}")

    

    def hay_datos_nuevos(self, df):
        """Compara fechas entre Excel y BD"""
        ultima_fecha_bd = self._obtener_ultima_fecha_bd()
        if ultima_fecha_bd is None: return True

        ultima_fecha_df = pd.to_datetime(df['fecha'].max()).date()
        logger.info(f"Comparando - BD: {ultima_fecha_bd} vs Excel: {ultima_fecha_df}")
        return ultima_fecha_df > ultima_fecha_bd

    def obtener_ultimo_valor_corrientes(self):
        self.conectar_bdd()
        # Si es Postgres (v2), usamos public.anac
        tabla = f"{self._get_schema_prefix()}anac"
        like_op = "ILIKE" if self.version == "2" else "LIKE"
        
        # Filtramos también por la cantidad > 0 para evitar errores
        query = f"""
            SELECT cantidad, fecha FROM {tabla} 
            WHERE aeropuerto {like_op} '%corrientes%' 
            AND cantidad > 0
            ORDER BY fecha DESC LIMIT 1
        """
        self.cursor.execute(query)
        result = self.cursor.fetchone()
        return (float(result[0]), result[1]) if result else (None, None)

    def _obtener_ultima_fecha_bd(self):
        self.conectar_bdd()
        prefix = self._get_schema_prefix()
        try:
            # Quitamos el 'public.' hardcodeado que tenías para que use el prefijo dinámico
            query = f"SELECT MAX(fecha) FROM {prefix}anac"
            self.cursor.execute(query)
            result = self.cursor.fetchone()
            # Libera el AccessShareLock de la consulta antes de que
            # SQLAlchemy abra otra conexión para modificar la tabla.
            self.conn.commit()
            if result and result[0]:
                return pd.to_datetime(result[0]).date()
            return None
        except Exception as e:
            self.conn.rollback()
            logger.info(f"Tabla no encontrada o vacía: {e}")
            return None

    def load_to_sheets(self, ultimo_valor, ultima_fecha):
        try:
            if ultimo_valor is None: return
            
            key_raw = os.getenv('GOOGLE_SHEETS_API_KEY')
            key_dict = loads(key_raw)
            
            # --- EL PARCHE PARA EL ERROR JWT ---
            if "\\n" in key_dict['private_key']:
                key_dict['private_key'] = key_dict['private_key'].replace("\\n", "\n")
            # ------------------------------------

            SPREADSHEET_ID = '1L_EzJNED7MdmXw_rarjhhX8DpL7HtaKpJoRwyxhxHGI'
            creds = service_account.Credentials.from_service_account_info(
                key_dict, scopes=['https://www.googleapis.com/auth/spreadsheets']
            )
            
            # Forzar actualización de token por si el reloj de la oficina está desfasado
            from google.auth.transport.requests import Request
            creds.refresh(Request())

            service = build('sheets', 'v4', credentials=creds, cache_discovery=False)
            
            meses_es = {1:"ene", 2:"feb", 3:"mar", 4:"abr", 5:"may", 6:"jun",
                        7:"jul", 8:"ago", 9:"sept", 10:"oct", 11:"nov", 12:"dic"}
            
            fecha_buscada = f"{meses_es[ultima_fecha.month]}-{str(ultima_fecha.year)[-2:]}"
            logger.info(f"Buscando columna para: {fecha_buscada}")

            res = service.spreadsheets().values().get(spreadsheetId=SPREADSHEET_ID, range="Datos!3:3").execute()
            headers = res.get("values", [[]])[0]
            
            col_idx = next((i for i, h in enumerate(headers) if h and str(h).strip().lower() == fecha_buscada.lower()), None)
            
            if col_idx is None:
                logger.warning(f"[WARN] No se encontró la columna '{fecha_buscada}'.")
                return

            letra_col = self.num_to_col(col_idx)
            rango_celda = f"Datos!{letra_col}10" 
            
            # Formato local (cambiar . por , si el Sheets está en español)
            val_str = str(float(ultimo_valor)).replace('.', ',')
            
            service.spreadsheets().values().update(
                spreadsheetId=SPREADSHEET_ID, range=rango_celda,
                valueInputOption='USER_ENTERED', body={'values': [[val_str]]}
            ).execute()
            
            logger.info(f"[OK] Sheets (ANAC) actualizado en {rango_celda}")

        except Exception as e:
            logger.error(f"Error en Sheets: {e}")

    def num_to_col(self, n):
        res = ""
        while n >= 0:
            res = chr(n % 26 + 65) + res
            n = n // 26 - 1
        return res
