import psycopg2
from sqlalchemy import create_engine, text
import pandas as pd
import os

class ConexionBase:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.port = 5432
        # Creamos el engine una sola vez para reutilizarlo
        self.engine_url = f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        self.engine = create_engine(self.engine_url)

    def conectar_bdd(self):
        """ Establece conexión vía psycopg2 para operaciones manuales/cursores """
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
                port=self.port,
                connect_timeout=10
            )
            self.cursor = self.conn.cursor()
            return self
        except Exception as e:
            print(f"Error al conectar: {e}")

    def probar_y_limpiar(self):
        """ Lee datos, hace el merge y limpia duplicados """
        self.conectar_bdd()
        
        # Usamos el engine de sqlalchemy para leer (más rápido y compatible)
        df_cobertura = pd.read_sql("SELECT * FROM cobertura_financiacion", self.engine)
        df_dicc = pd.read_sql("SELECT * FROM cobertura_financiacion_dicc", self.engine)

        # Limpieza de diccionarios
        df_dicc = df_dicc.drop_duplicates(subset=['ciiu'], keep='first')

        # Merge
        df_final = df_cobertura.merge(df_dicc[['ciiu', 'desc_ciiu']], on='ciiu', how='left')
        df_final.rename(columns={'desc_ciiu': 'ciiu_descripcion'}, inplace=True)
        
        print("Muestra de datos procesados:")
        print(df_final.head())
        return df_final

    def carga_bdd(self, df, tabla, schema='public'):
        """ Realiza la carga al nuevo servidor """
        print(f"\n>>> Iniciando carga en tabla: {tabla} ({self.database})")
        
        try:
            # if_exists='append' mantiene los datos y suma los nuevos
            df.to_sql(name=tabla, con=self.engine, schema=schema, if_exists='append', index=False)
            try:
                full_table = f"{schema}.{tabla}" if schema else tabla
                with self.engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE {full_table} ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
            except Exception as e:
                print(f"Error al agregar columna updated_at: {e}")
            print(f"ÉXITO: {len(df)} filas insertadas en {tabla}")
        except Exception as e:
            print(f"ERROR en carga: {e}")

    def main(self, df_a_cargar):
        # 1. Conectar
        self.conectar_bdd()
        
        # 2. Cargar la tabla principal (srt según tu ejemplo)
        # Asegúrate de que las columnas del DF coincidan con la tabla en Postgres
        self.carga_bdd(df_a_cargar, 'srt')

        # 3. Cerrar conexiones
        self.conn.commit()
        self.cursor.close()
        self.conn.close()
        print("Conexiones cerradas correctamente.")