import pandas as pd
from sqlalchemy import create_engine, text
import re
import logging

logger = logging.getLogger(__name__)

class connection_db:

    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.version = str(version) # "1" para MySQL, "2" para Postgres
        self.tabla = "cbt_cba"
        self.engine = None

    #Conexion a la BDD
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
            logger.info(f"[LOAD CBT] Conexión establecida a la base de datos '{self.database}' (v{self.version}).")

    def _get_schema(self):
        return "public" if self.version == "2" else None

    #Objetivo: Almacenar los datos de CBA y CBT sin procesar en el datalake. Datos sin procesar
    def load_datalake(self,df: pd.DataFrame) -> bool:
        """Carga incremental híbrida para el Datalake."""
        logger.info("[LOAD CBT] Iniciando proceso de carga a la base de datos.")
        self._conectar()
        schema = self._get_schema()
        full_table = f"{schema}.{self.tabla}" if schema else self.tabla

        # Aseguramos que los tipos de datos sean numéricos y redondeamos
        cols_numericas = ['cba_adulto', 'cbt_adulto', 'cba_hogar', 'cbt_hogar', 'cba_nea', 'cbt_nea']
        for col in cols_numericas:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').round(2)

        # 2. Comparativa de conteo
        with self.engine.connect() as conn:
            try:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {full_table}"))
                len_bdd = res.scalar()
            except Exception:
                len_bdd = 0
                logger.info(f"[LOAD CBT] La tabla '{self.tabla}' no existe, se creará una nueva.")

        # 3. Carga si hay novedades (más filas o diferencias en el último registro)
        novedades = False
        if len(df) > len_bdd:
            novedades = True
        elif len(df) == len_bdd and len_bdd > 0:
            with self.engine.connect() as conn:
                try:
                    # 1. Comparamos la fecha del último registro
                    res_db = conn.execute(text(f"SELECT fecha FROM {full_table} ORDER BY fecha DESC LIMIT 1")).fetchone()
                    if res_db:
                        db_fecha = res_db[0]
                        last_df = df.sort_values(by='fecha').iloc[-1]
                        df_fecha = pd.to_datetime(last_df['fecha']).date()
                        if isinstance(db_fecha, str):
                            db_fecha = pd.to_datetime(db_fecha).date()
                        elif hasattr(db_fecha, 'date'):
                            db_fecha = db_fecha.date()
                        
                        if df_fecha != db_fecha:
                            novedades = True
                            logger.info("[LOAD CBT] Novedad detectada: La fecha del último registro difiere. Se actualizará la tabla.")
                    
                    # 2. Comparamos la suma total de valores para detectar correcciones históricas
                    res_sum = conn.execute(text(f"SELECT SUM(cba_nea), SUM(cbt_nea) FROM {full_table}")).fetchone()
                    if res_sum:
                        db_sum_cba, db_sum_cbt = res_sum
                        df_sum_cba = df['cba_nea'].sum()
                        df_sum_cbt = df['cbt_nea'].sum()
                        
                        val_db_sum_cba = float(db_sum_cba) if db_sum_cba is not None else 0.0
                        val_df_sum_cba = float(df_sum_cba) if pd.notna(df_sum_cba) else 0.0
                        val_db_sum_cbt = float(db_sum_cbt) if db_sum_cbt is not None else 0.0
                        val_df_sum_cbt = float(df_sum_cbt) if pd.notna(df_sum_cbt) else 0.0
                        
                        if abs(val_df_sum_cba - val_db_sum_cba) > 1.0 or abs(val_df_sum_cbt - val_db_sum_cbt) > 1.0:
                            novedades = True
                            logger.info("[LOAD CBT] Novedad detectada: Se encontraron correcciones en datos históricos del NEA. Se actualizará la tabla.")
                            
                except Exception as e:
                    logger.warning(f"[LOAD CBT] Error al comparar registros históricos: {e}")

        if novedades:
            # Ordenamos por fecha antes de insertar
            df = df.sort_values(by='fecha', ascending=True)
            
            logger.info("[LOAD CBT] Iniciando TRUNCATE e INSERT en la tabla '%s'.", full_table)
            with self.engine.begin() as conn:
                # Truncate
                if self.version == "2":
                    conn.execute(text(f"TRUNCATE TABLE {full_table} CASCADE"))
                else:
                    conn.execute(text(f"TRUNCATE TABLE {full_table}"))
                
                # Inserción masiva con SQLAlchemy (adiós a los loops de cursores)
                df.to_sql(
                    name=self.tabla, 
                    con=conn, 
                    schema=schema, 
                    if_exists='append', 
                    index=False, 
                    method='multi'
                )
            
            ultima_fecha = df['fecha'].iloc[-1]
            logger.info(f"[LOAD CBT] Carga completada: {len(df)} filas insertadas en '{self.tabla}'. Última fecha: {ultima_fecha}")
            return True
        
        logger.info(f"[LOAD CBT] No se detectaron datos nuevos para cargar. BDD: {len_bdd} filas | DF: {len(df)} filas.")
        return False
    
    def close(self):
        """Cierra el pool de conexiones del motor."""
        if self.engine:
            self.engine.dispose()
            self.engine = None
            logger.info("[LOAD CBT] Conexiones a la base de datos cerradas.")
