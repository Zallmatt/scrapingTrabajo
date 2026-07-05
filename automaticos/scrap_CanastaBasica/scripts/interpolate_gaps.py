import os
import sys
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Agregar directorio raíz del proyecto para imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    load_dotenv()
    
    def get_url(prefix):
        host = os.getenv(f'HOST_{prefix}')
        user = os.getenv(f'USER_{prefix}')
        pw = os.getenv(f'PASSWORD_{prefix}')
        db_env = 'NAME_DB_CANASTA' if prefix == 'DBB2' else 'NAME_DB_CANASTA_V1'
        db_default = 'canasta_basica_super' if prefix == 'DBB2' else 'canasta_basica_supermercados'
        db = os.getenv(db_env, db_default)
        port = os.getenv(f'PORT_{prefix}', '5432' if prefix == 'DBB2' else '3306')
        if prefix == 'DBB2':
            return f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"
        else:
            return f"mysql+pymysql://{user}:{pw}@{host}:{port}/{db}"

    engine_v1 = create_engine(get_url('DBB1'))
    engine_v2 = create_engine(get_url('DBB2'))
    
    date_start = '2026-07-02'
    date_end = '2026-07-05'
    missing_dates = ['2026-07-03', '2026-07-04']
    
    print(f"=== INTERPOLACIÓN LINEAL DE PRECIOS ({date_start} -> {date_end}) ===")
    
    try:
        # 1. Limpiar datos previos
        for m_date in missing_dates:
            print(f"Limpiando {m_date}...")
            with engine_v1.begin() as conn:
                conn.execute(text(f"DELETE FROM precios_productos WHERE fecha_extraccion = '{m_date}'"))
            with engine_v2.begin() as conn:
                conn.execute(text(f"DELETE FROM precios_productos WHERE fecha_extraccion = '{m_date}'"))

        # 2. Obtener datos
        print("Obteniendo datos...")
        q = text("SELECT id_link_producto, precio_normal, precio_descuento, precio_por_unidad, peso, nombre_producto, unidad_medida FROM precios_productos WHERE fecha_extraccion = :fecha")
        
        with engine_v2.connect() as conn:
            df_start = pd.read_sql(q, conn, params={"fecha": date_start}).drop_duplicates('id_link_producto')
            df_end = pd.read_sql(q, conn, params={"fecha": date_end}).drop_duplicates('id_link_producto')
        
        merged = pd.merge(df_start, df_end, on='id_link_producto', suffixes=('_start', '_end'))
        print(f"Productos coincidentes: {len(merged)}")

        # 3. Interpolar e Insertar
        total_days = len(missing_dates) + 1
        for i, m_date in enumerate(missing_dates):
            day_num = i + 1 
            print(f"Procesando {m_date}...")
            
            # MySQL
            with engine_v1.begin() as conn:
                conn.execute(text("INSERT INTO extracciones (fecha_inicio, fecha_fin, estado, productos_extraidos, productos_exitosos, productos_fallidos, duracion_segundos, created_at) VALUES (NOW(), NOW(), 'completada', :total, :total, 0, 0, NOW())"), {"total": len(merged)})
                res = conn.execute(text("SELECT LAST_INSERT_ID()"))
                id_ext = res.scalar()
            
            # Postgres
            with engine_v2.begin() as conn:
                conn.execute(text("INSERT INTO extracciones (id_extraccion, fecha_inicio, fecha_fin, estado, productos_extraidos, productos_exitosos, productos_fallidos, duracion_segundos, created_at) VALUES (:id, NOW(), NOW(), 'completada', :total, :total, 0, 0, NOW())"), {"id": id_ext, "total": len(merged)})

            df_i = merged.copy()
            for col in ['precio_normal', 'precio_descuento', 'precio_por_unidad']:
                df_i[col] = (df_i[f'{col}_start'] + (df_i[f'{col}_end'] - df_i[f'{col}_start']) * (day_num / total_days)).round(2)
            
            df_final = pd.DataFrame()
            df_final['id_link_producto'] = df_i['id_link_producto']
            df_final['id_extraccion'] = id_ext
            df_final['nombre_producto'] = df_i['nombre_producto_start']
            df_final['precio_normal'] = df_i['precio_normal']
            df_final['precio_descuento'] = df_i['precio_descuento']
            df_final['precio_por_unidad'] = df_i['precio_por_unidad']
            df_final['unidad_medida'] = df_i['unidad_medida_start']
            df_final['peso'] = df_i['peso_start']
            df_final['fecha_extraccion'] = datetime.strptime(m_date, '%Y-%m-%d').date()
            df_final['created_at'] = datetime.now()
            
            print(f" - Insertando {len(df_final)} filas (ID Extraccion: {id_ext})...")
            batch_size = 500
            for start in range(0, len(df_final), batch_size):
                batch = df_final.iloc[start:start+batch_size]
                with engine_v1.begin() as conn:
                    batch.to_sql('precios_productos', conn, if_exists='append', index=False)
                with engine_v2.begin() as conn:
                    batch.to_sql('precios_productos', conn, if_exists='append', index=False)
            
        print("\n=== INTERPOLACIÓN COMPLETADA CON ÉXITO ===")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        engine_v1.dispose()
        engine_v2.dispose()

if __name__ == "__main__":
    main()
