"""
LOAD - Módulo de carga de datos RIPTE
Responsabilidad: Insertar el nuevo valor de RIPTE si difiere del último en BD
"""
import logging
import pandas as pd
import pymysql
import psycopg2
from datetime import datetime, timedelta
import calendar
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

class LoadRIPTE:
    """Carga el valor RIPTE de forma incremental soportando MySQL y Postgres."""

    def __init__(self, host, user, password, database, port=None, version="1"):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = port
        self.version = str(version)
        self.tabla = 'ripte'
        self.tolerancia = 100
        self.engine = None

    def _conectar(self):
        """Crea el motor de conexión según la versión."""
        if self.engine is None:
            if self.version == "1":
                puerto = int(self.port) if self.port else 3306
                url = f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            else:
                puerto = int(self.port) if self.port else 5432
                url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{puerto}/{self.database}"
            
            self.engine = create_engine(url)
            logger.info(f"[OK] Motor RIPTE conectado (v{self.version})")

    def load(self, valor: float) -> bool:
        self._conectar()
        schema = "public." if self.version == "2" else ""
        full_table = f"{schema}{self.tabla}"
        
        with self.engine.begin() as conn:
            # 1. Obtener último registro
            res = conn.execute(text(f"SELECT fecha, valor FROM {full_table} ORDER BY fecha DESC LIMIT 1"))
            row = res.fetchone()
            
            if row:
                ultima_fecha, ultimo_ripte = row
                fecha_db_str = pd.to_datetime(ultima_fecha).strftime('%Y-%m-%d')
                
                # 2. Validar cambio significativo
                if abs(valor - float(ultimo_ripte)) < self.tolerancia:
                    logger.info(f"[LOAD] Comparación -> Base: {fecha_db_str} (Valor: {ultimo_ripte}) | Extraído: (Valor: {valor})")
                    logger.info(f"[LOAD] No hay datos nuevos. La base llega hasta {fecha_db_str}. No se sube a la base ni al Sheets.")
                    return False
                
                # 3. Calcular nueva fecha
                fecha_base = pd.to_datetime(ultima_fecha)
                _, dias_mes = calendar.monthrange(fecha_base.year, fecha_base.month)
                nueva_fecha = fecha_base + timedelta(days=dias_mes)
                fecha_ext_str = nueva_fecha.strftime('%Y-%m-%d')
                
                logger.info(f"[LOAD] Comparación de fechas -> Base: {fecha_db_str} | Extraído (Nuevo período): {fecha_ext_str}")
                logger.info(f"[LOAD] ¡Datos nuevos detectados! Valor base: {ultimo_ripte} -> Nuevo valor: {valor}")
            else:
                # Si tabla vacía, usamos fecha actual o inicio de año
                nueva_fecha = datetime.now().replace(day=1)
                fecha_ext_str = nueva_fecha.strftime('%Y-%m-%d')
                logger.info(f"[LOAD] Comparación de fechas -> Base: Ninguna (Tabla vacía) | Extraído: {fecha_ext_str}")
                logger.info("[LOAD] ¡Datos nuevos detectados! Se insertará el primer registro.")

            # 4. Insertar nuevo valor
            conn.execute(
                text(f"INSERT INTO {full_table} (fecha, valor) VALUES (:f, :v)"),
                {"f": nueva_fecha, "v": valor}
            )
            try:
                alter_query = f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;" if self.version == "2" else f"ALTER TABLE {full_table} ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
                conn.execute(text(alter_query))
            except Exception as e:
                logger.warning(f"[LOAD] No se pudo agregar la columna updated_at: {e}")
            logger.info("[LOAD] Carga a la base completada.")
            return True

    def close(self):
        if self.engine:
            self.engine.dispose()
            self.engine = None