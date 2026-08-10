"""
LOAD - Módulo de carga de datos OEDE
Responsabilidad: Cargar solo filas nuevas a PostgreSQL
"""
import logging
import pandas as pd
import psycopg2
import pymysql
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

TABLA = "oede" 

class LoadOEDE:
    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.version = str(version)
        self.engine = None
        self.tabla = "oede"

    def _conectar(self):
        if self.engine is None:
            if self.version == "1":  # MySQL
                puerto = int(self.port) if self.port else 3306
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            else:  # PostgreSQL
                puerto = int(self.port) if self.port else 5432
                url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            
            self.engine = create_engine(url, echo=False)
            logger.info(f"[OK] Motor conectado a OEDE (v{self.version})")

    def load(self, df: pd.DataFrame) -> bool:
        self._conectar()
        schema = "public" if self.version == "2" else None
        full_table = f"{schema}.{self.tabla}" if schema else self.tabla

        # 1. Asegurar formato fecha y obtener fechas del nuevo DF
        df['fecha'] = pd.to_datetime(df['fecha']).dt.date
        fechas_nuevas_df = sorted(list(df['fecha'].unique()))
        fecha_max_extract = max(fechas_nuevas_df) if fechas_nuevas_df else None

        # 2. Obtener fechas existentes en la BDD
        try:
            with self.engine.connect() as conn:
                query_fechas_db = f"SELECT DISTINCT fecha FROM {full_table}"
                fechas_existentes_db = set(pd.read_sql(query_fechas_db, conn)['fecha'])

                query_max_fecha_db = f"SELECT MAX(fecha) FROM {full_table}"
                fecha_max_db = conn.execute(text(query_max_fecha_db)).scalar()
        except Exception:  # La tabla podría no existir
            fechas_existentes_db = set()
            fecha_max_db = None

        # 3. Logging de comparación de fechas
        fecha_db_str = fecha_max_db.strftime('%Y-%m-%d') if hasattr(fecha_max_db, 'strftime') else 'Ninguna (Tabla vacía)'
        fecha_ext_str = fecha_max_extract.strftime('%Y-%m-%d') if hasattr(fecha_max_extract, 'strftime') else 'Ninguna (DF vacío)'
        logger.info(f"[LOAD] Comparación de fechas -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")

        # 4. Determinar qué se va a hacer (actualizar, insertar, o ambos)
        fechas_a_actualizar = sorted([f for f in fechas_nuevas_df if f in fechas_existentes_db])
        fechas_a_insertar_nuevas = sorted([f for f in fechas_nuevas_df if f not in fechas_existentes_db])

        if not fechas_a_actualizar and not fechas_a_insertar_nuevas:
            logger.info("[LOAD] No hay datos nuevos o diferentes para procesar.")
            return True  # No es un error, simplemente no hay nada que hacer

        # 5. Estrategia UPSERT (Delete por fecha antes de Insert)
        with self.engine.begin() as conn:
            # Borramos los registros de trimestres que se van a refrescar
            if fechas_a_actualizar:
                logger.info(f"[LOAD] Se reemplazarán los datos para {len(fechas_a_actualizar)} trimestres existentes.")
                conn.execute(text(f"DELETE FROM {full_table} WHERE fecha IN :fechas"),
                             {"fechas": tuple(fechas_a_actualizar)})

            if fechas_a_insertar_nuevas:
                logger.info(f"[LOAD] Se insertarán datos para {len(fechas_a_insertar_nuevas)} trimestres nuevos.")

            # 6. Carga limpia de todos los datos del DF
            df.to_sql(
                name=self.tabla, con=conn, schema=schema,
                if_exists='append', index=False, method='multi'
            )
            try:
                alter_query = f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                conn.execute(text(alter_query))
            except Exception as e:
                logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")

        logger.info(f"[LOAD] Carga a la base completada. Se subieron {len(df)} registros a la tabla '{self.tabla}'.")
        return True

    def close(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None