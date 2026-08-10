"""
LOAD - Módulo de carga de datos IPI
Responsabilidad: Cargar las 3 tablas del IPI a MySQL (incremental)
"""
import os
import logging
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text
from google.oauth2 import service_account
from googleapiclient.discovery import build
from json import loads

logger = logging.getLogger(__name__)

logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

class LoadIPI:
    """Carga los DataFrames del IPI a PostgreSQL/MySQL de forma incremental."""

    def __init__(self, host, user, password, db_datalake, db_dwh, port, version="2"):
        self.host = host
        self.user = user
        self.password = password
        self.db_datalake = db_datalake
        self.db_dwh = db_dwh
        self.port = port
        self.version = str(version)
        self.engines = {}

    def _get_engine(self, db_name):
        """Crea o retorna el motor de conexión para una base de datos específica."""
        if db_name not in self.engines:
            if self.version == "1":  # MySQL
                port = int(self.port) if self.port else 3306
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{port}/{db_name}"
            else:  # PostgreSQL
                port = int(self.port) if self.port else 5432
                url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{port}/{db_name}"
            
            self.engines[db_name] = create_engine(url, echo=False)
            logger.info(f"[OK] Motor conectado a base '{db_name}' (v{self.version})")
        return self.engines[db_name]

    def _get_schema(self):
        return "public" if self.version == "2" else None

    def load(self, dfs_dict: dict):
        """Carga el diccionario de DataFrames en sus respectivas bases de datos."""
        
        # 1. Definir mapeo: clave del dict -> (base_datos, nombre_tabla_bdd)
        if self.version == "1":
            # Todo va al datalake
            configuracion = {
                'valores': (self.db_datalake, 'ipi'),
                'variaciones': (self.db_datalake, 'ipi_variacion_interanual'),
                'acumulado': (self.db_datalake, 'ipi_variacion_interacumulada')
            }
        else:
            # v2: Separación entre datalake y dwh
            configuracion = {
                'valores': (self.db_datalake, 'ipi'),
                'variaciones': (self.db_dwh, 'ipi_variacion_interanual'),
                'acumulado': (self.db_dwh, 'ipi_variacion_interacumulada')
            }

        schema = self._get_schema()

        # 2. Iterar sobre cada tabla
        for key, (db_name, tabla) in configuracion.items():
            df = dfs_dict[key]
            if df.empty:
                logger.warning(f"[LOAD] [{key.upper()}] DataFrame vacío, omitiendo carga para tabla '{tabla}'.")
                continue

            engine = self._get_engine(db_name)
            
            logger.info(f"--- Iniciando carga para: {key.upper()} (Tabla: {tabla}, Base: {db_name}) ---")

            # Asegurar formato fecha y obtener info del DF
            df['fecha'] = pd.to_datetime(df['fecha']).dt.date
            fecha_max_extract = df['fecha'].max()

            full_table = f"{schema}.{tabla}" if schema else tabla

            # Obtener info de la BDD para logging
            try:
                with engine.connect() as conn:
                    fecha_max_db = conn.execute(text(f"SELECT MAX(fecha) FROM {full_table}")).scalar()
            except Exception:
                fecha_max_db = None

            # Logging de comparación
            fecha_db_str = fecha_max_db.strftime('%Y-%m-%d') if hasattr(fecha_max_db, 'strftime') else 'Ninguna (Tabla vacía)'
            fecha_ext_str = fecha_max_extract.strftime('%Y-%m-%d') if hasattr(fecha_max_extract, 'strftime') else 'Ninguna (DF vacío)'
            logger.info(f"[LOAD] [{key.upper()}] Comparación de fechas -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")

            # La lógica de refresco es borrar e insertar, lo cual es correcto si hay correcciones en los datos.
            logger.info(f"[LOAD] [{key.upper()}] Refrescando/insertando datos para {len(df['fecha'].unique())} meses. Se subirán {len(df)} registros.")

            with engine.begin() as conn:
                # Borrado seguro por fechas para evitar duplicados
                fechas = tuple(df['fecha'].unique().tolist())
                conn.execute(text(f"DELETE FROM {full_table} WHERE fecha IN :fechas"), {"fechas": fechas})
                
                # Carga
                df.to_sql(tabla, conn, schema=schema, if_exists='append', index=False, method='multi')
                try:
                    alter_query = f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    conn.execute(text(alter_query))
                except Exception as e:
                    logger.warning(f"[LOAD] [{key.upper()}] No se pudo agregar la columna updated_at a {full_table}: {e}")
                
        logger.info("[OK] Carga de datos del IPI completada.")

    def close(self):
        """Cierra todos los motores de conexión abiertos."""
        for db_name, engine in self.engines.items():
            engine.dispose()
            logger.info(f"[LOAD] Conexión a '{db_name}' cerrada.")
        self.engines = {}