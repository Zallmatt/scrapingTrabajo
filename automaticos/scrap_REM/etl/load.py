"""
LOAD - Módulo de carga de datos REM
Responsabilidad: Cargar precios minoristas y cambio nominal a MySQL
"""
import logging
import pandas as pd
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

class LoadREM:
    """Carga los datos del REM a MySQL/PostgreSQL de forma híbrida."""

    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.version = str(version)
        self.engine = None
        self.tabla_cambio = "rem_precios_minoristas"

    def _conectar(self):
        """Crea el motor de conexión dinámico."""
        if self.engine is None:
            if self.version == "1":
                puerto = int(self.port) if self.port else 3306
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            else:
                puerto = int(self.port) if self.port else 5432
                url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            
            self.engine = create_engine(url, echo=False)
            logger.info(f"[OK] Motor conectado a '{self.database}' (v{self.version})")

    def _get_schema(self):
        return "public" if self.version == "2" else None

    def load(self, df_new: pd.DataFrame):
        """Carga la tabla de precios minoristas (haciendo append de nuevas consultas)."""
        self._conectar()
        schema = self._get_schema()

        try:
            # Obtenemos info de los datos recién extraídos para los logs
            fecha_consulta_new = df_new['fecha_consulta'].max()
            fecha_min_ext = pd.to_datetime(df_new['fecha'].min())
            fecha_max_ext = pd.to_datetime(df_new['fecha'].max())
            fecha_ext_str = fecha_consulta_new.strftime('%Y-%m-%d') if hasattr(fecha_consulta_new, 'strftime') else str(fecha_consulta_new)

            # 1. Intentamos leer la última fecha de consulta cargada
            query = f"SELECT MAX(fecha_consulta) FROM {self.tabla_cambio}"
            with self.engine.connect() as conn:
                last_date = conn.execute(text(query)).scalar()

            if last_date is not None:
                fecha_db_str = last_date.strftime('%Y-%m-%d') if hasattr(last_date, 'strftime') else str(last_date)
                logger.info(f"[LOAD] Comparación de fecha de consulta -> Base: {fecha_db_str} | Extraído: {fecha_ext_str}")

                # 2. Traemos la última carga para comparar
                query_last_data = f"SELECT fecha, mediana FROM {self.tabla_cambio} WHERE fecha_consulta = :last_date"
                df_old = pd.read_sql(text(query_last_data), self.engine, params={"last_date": last_date})
                
                # Convertimos fechas a datetime para comparar bien
                df_old['fecha'] = pd.to_datetime(df_old['fecha'])
                
                # 3. Comparación: ¿Son iguales la fecha y la mediana?
                # Ordenamos ambos para que la comparación sea justa
                check_columns = ['fecha', 'mediana']
                df_new_sorted = df_new[check_columns].sort_values('fecha').reset_index(drop=True)
                df_old_sorted = df_old[check_columns].sort_values('fecha').reset_index(drop=True)

                if df_new_sorted.equals(df_old_sorted):
                    logger.info(f"[LOAD] No hay datos nuevos. La curva de expectativas extraída es idéntica a la cargada en la base ({fecha_db_str}). No se sube a la base.")
                    return # Cortamos la ejecución aquí
            else:
                logger.info(f"[LOAD] Comparación de fecha de consulta -> Base: Ninguna (Tabla vacía) | Extraído: {fecha_ext_str}")

            logger.info(f"[LOAD] ¡Datos nuevos detectados! Se cargarán {len(df_new)} registros (Períodos proyectados: {fecha_min_ext.strftime('%Y-%m')} a {fecha_max_ext.strftime('%Y-%m')}).")

            # 4. Si no son iguales o la tabla está vacía, cargamos
            with self.engine.begin() as conn:
                df_new.to_sql(
                    name=self.tabla_cambio, 
                    con=conn, 
                    schema=schema, 
                    if_exists='append',
                    index=False, 
                    method='multi'
                )
                try:
                    full_table = f"{schema}.{self.tabla_cambio}" if schema else self.tabla_cambio
                    alter_query = f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    conn.execute(text(alter_query))
                except Exception as e:
                    logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")
            logger.info("[LOAD] Carga a la base completada.")

        except Exception as e:
            # Si la tabla no existe (primera vez), la creamos directamente
            logger.warning("[LOAD] Error al comparar (posible tabla nueva): %s", e)
            logger.info(f"[LOAD] ¡Creando tabla y haciendo carga inicial! Se subirán {len(df_new)} registros.")
            df_new.to_sql(name=self.tabla_cambio, con=self.engine, schema=schema, if_exists='append', index=False)
            try:
                full_table = f"{schema}.{self.tabla_cambio}" if schema else self.tabla_cambio
                with self.engine.begin() as conn:
                    alter_query = f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                    conn.execute(text(alter_query))
            except Exception as e:
                logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")
            logger.info("[LOAD] Carga a la base completada.")

    def close(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None