import mysql.connector
import pandas as pd
from datetime import datetime
import calendar
from email.message import EmailMessage
import ssl
import smtplib

class connect_db:
    def connect_db_tasas(self, df, host, user, password, database):
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()

        table_name= 'ecv_tasas'
        select_row_count_query = f"SELECT COUNT(*) FROM {table_name}"
        cursor.execute(select_row_count_query)
        filas_BD = cursor.fetchone()[0]
        print("Base: ", filas_BD)
        print("DF", len(df))
        longitud_df = len(df)

        if filas_BD != len(df):
            df_datos_nuevos = df.tail(longitud_df - filas_BD)

            print("aca:", df_datos_nuevos)
            print("Tabla de ECV")
            for index, row in df_datos_nuevos.iterrows():
                # Luego, puedes usar estos valores en tu consulta SQL
                sql_insert = f"INSERT INTO {table_name} (fecha, trimestre, aglomerado, tasa_de_empleo, tasa_de_desocupacion, tasa_de_actividad, tasa_de_inactividad) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                # Ejecutar la sentencia SQL de inserción
                cursor.execute(sql_insert, (row['Fecha'], row['Trimestre'], row['Aglomerado'], row['Tasa de empleo'], row['Tasa de desocupación'], row['Tasa de actividad'], row['Tasa de inactividad']))
            conn.commit()
            df_datos_nuevos['Fecha'] = pd.to_datetime(df_datos_nuevos['Fecha'], format='%Y-%m-%d')
        else: 
            print("Se verifico la tabla de IPICORR")
            
        cursor.close()
        conn.close()

    def connect_db_trabajo(self, df, host, user, password, database): 
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()

        table_name= 'ecv_trabajo'
        select_row_count_query = f"SELECT COUNT(*) FROM {table_name}"
        cursor.execute(select_row_count_query)
        filas_BD = cursor.fetchone()[0]
        print("Base: ", filas_BD)
        print("DF", len(df))
        longitud_df = len(df)

        if filas_BD != len(df):
            df_datos_nuevos = df.tail(longitud_df - filas_BD)

            print("aca:", df_datos_nuevos)
            print("Tabla de ECV")
            for index, row in df_datos_nuevos.iterrows():
                # Luego, puedes usar estos valores en tu consulta SQL
                sql_insert = f"INSERT INTO {table_name} (aglomerado, año, fecha, trimestre, tasa_de_actividad, tasa_de_empleo, tasa_de_desocupación, empleo_privado, empleo_público, empleo_otro, empleo_privado_registrado, empleo_privado_no_registrado, salario_promedio_público, salario_promedio_privado, salario_promedio_privado_registrado, salario_promedio_privado_no_registrado, patron, cuenta_propia, empleado_obrero, trabajador_familiar_sin_remuneración) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

                # Ejecutar la sentencia SQL de inserción
                cursor.execute(sql_insert, (row['Aglomerado'], row['Año'], row['Fecha'], row['Trimestre'], row['Tasa de Actividad'], row['Tasa de Empleo'], row['Tasa de desocupación'], row['Empleo Privado'], row['Empleo Público'], row['Empleo Otro'], row['Empleo Privado Registrado'], row['Empleo Privado No Registrado'], row['Salario Promedio Público'], row['Salario Promedio Privado'], row['Salario Promedio Privado Registrado'], row['Salario Promedio Privado No Registrado'], row['Patron'], row['Cuenta Propia'], row['Empleado/Obrero'], row['Trabajador familiar sin remuneración']))
            conn.commit()
            df_datos_nuevos['Fecha'] = pd.to_datetime(df_datos_nuevos['Fecha'], format='%Y-%m-%d')
        else: 
            print("Se verifico la tabla de IPICORR")
            
        cursor.close()
        conn.close()

    def connect_db_trabajo_quintiles(self, df, host, user, password, database): 
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()

        table_name= 'ecv_trabajo_quintiles'
        select_row_count_query = f"SELECT COUNT(*) FROM {table_name}"
        cursor.execute(select_row_count_query)
        filas_BD = cursor.fetchone()[0]
        print("Base: ", filas_BD)
        print("DF", len(df))
        longitud_df = len(df)

        if filas_BD != len(df):
            df_datos_nuevos = df.tail(longitud_df - filas_BD)

            print("aca:", df_datos_nuevos)
            print("Tabla de ECV")
            for index, row in df_datos_nuevos.iterrows():
                # Luego, puedes usar estos valores en tu consulta SQL
                sql_insert = f"INSERT INTO {table_name} (aglomerado, año, fecha, trimestre, quintil, empleo_público, empleo_privado, empleo_otro, patron, cuenta_propia, obrero_o_empleado, trabajador_familiar_sin_remuneracion, primaria_incompleta, primaria_completa, secundaria_incompleta, secundaria_completa, superior_o_universitario_incompleto, superior_o_universitario_completo, sin_instruccion) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                # Ejecutar la sentencia SQL de inserción
                cursor.execute(sql_insert, (row['Aglomerado'], row['Año'], row['Fecha'], row['Trimestre'], row['Quintil'], 
                row['Empleo Público'], row['Empleo Privado'], row['Empleo Otro'], 
                row['Patron'], row['Cuenta Propia'], row['Obrero o Empleado'], 
                row['Trabajador Familiar sin Remuneracion'], row['Primaria Incompleta'], 
                row['Primaria Completa'], row['Secundaria Incompleta'], 
                row['Secundaria Completa'], row['Superior o Universitario Incompleto'], 
                row['Superior o Universitario Completo'], row['Sin Instruccion']))
            conn.commit()
            df_datos_nuevos['Fecha'] = pd.to_datetime(df_datos_nuevos['Fecha'], format='%Y-%m-%d')
        else: 
            print("Se verifico la tabla de IPICORR")
            
        cursor.close()
        conn.close()

    def connect_db_salud_cobertura(self, df, host, user, password, database): 
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()

        table_name= 'ecv_salud_cobertura'
        select_row_count_query = f"SELECT COUNT(*) FROM {table_name}"
        cursor.execute(select_row_count_query)
        filas_BD = cursor.fetchone()[0]
        print("Base: ", filas_BD)
        print("DF", len(df))
        longitud_df = len(df)

        if filas_BD != len(df):
            df_datos_nuevos = df.tail(longitud_df - filas_BD)

            print("aca:", df_datos_nuevos)
            print("Tabla de ECV")
            for index, row in df_datos_nuevos.iterrows():
                # Luego, puedes usar estos valores en tu consulta SQL
                sql_insert = f"INSERT INTO {table_name} (aglomerado, año, fecha, semestre, cobertura, planes_y_seguros, no_paga_ni_le_descuentan) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                # Ejecutar la sentencia SQL de inserción
                cursor.execute(sql_insert, (row['Aglomerado'], row['Año'], row['Fecha'], row['Semestre'], row['Cobertura'], 
                row['Planes y seguros'], row['No paga ni le descuentan']))
            conn.commit()
            df_datos_nuevos['Fecha'] = pd.to_datetime(df_datos_nuevos['Fecha'], format='%Y-%m-%d')
        else: 
            print("Se verifico la tabla de IPICORR")
            
        cursor.close()
        conn.close()

    def connect_db_salud_consulta_establecimiento(self, df, host, user, password, database): 
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()

        table_name= 'ecv_salud_consulta_establecimiento'
        select_row_count_query = f"SELECT COUNT(*) FROM {table_name}"
        cursor.execute(select_row_count_query)
        filas_BD = cursor.fetchone()[0]
        print("Base: ", filas_BD)
        print("DF", len(df))
        longitud_df = len(df)

        if filas_BD != len(df):
            df_datos_nuevos = df.tail(longitud_df - filas_BD)

            print("aca:", df_datos_nuevos)
            print("Tabla de ECV")
            for index, row in df_datos_nuevos.iterrows():
                # Luego, puedes usar estos valores en tu consulta SQL
                sql_insert = f"INSERT INTO {table_name} (aglomerado, año, fecha, semestre, cobertura, si_consulto, no_consulto, dolencia_afeccion_enfermedad, control_prevencion, establecimiento_privado, establecimiento_publico) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"

                # Rellenar los valores faltantes (NaN) con None
                row = row.where(pd.notnull(row), None)
                
                # Ejecutar la sentencia SQL de inserción
                cursor.execute(sql_insert, (row['Aglomerado'], row['Año'], row['Fecha'], row['Semestre'], row['Cobertura'], 
                                row['Si consulto'], row['No consulto'], row['Dolencia/ afección/ enfermedad'], row['Control/ prevención'], row['Establecimiento_Privado'], row['Establecimiento_Publico']))
            conn.commit()
            df_datos_nuevos['Fecha'] = pd.to_datetime(df_datos_nuevos['Fecha'], format='%Y-%m-%d')

        else: 
            print("Se verifico la tabla de IPICORR")
            
        cursor.close()
        conn.close()

    def connect_db_salud_quintil_consulta(self, df, host, user, password, database): 
        conn = mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database
        )
        cursor = conn.cursor()

        table_name= 'ecv_salud_quintil_consulta'
        select_row_count_query = f"SELECT COUNT(*) FROM {table_name}"
        cursor.execute(select_row_count_query)
        filas_BD = cursor.fetchone()[0]
        print("Base: ", filas_BD)
        print("DF", len(df))
        longitud_df = len(df)

        if filas_BD != len(df):
            df_datos_nuevos = df.tail(longitud_df - filas_BD)

            print("aca:", df_datos_nuevos)
            print("Tabla de ECV")
            for index, row in df_datos_nuevos.iterrows():
                # Luego, puedes usar estos valores en tu consulta SQL
                sql_insert = f"INSERT INTO {table_name} (aglomerado, año, fecha, semestre, cobertura, quintil, si_consulto, no_consulto) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"

                # Rellenar los valores faltantes (NaN) con None
                row = row.where(pd.notnull(row), None)
                
                # Ejecutar la sentencia SQL de inserción
                cursor.execute(sql_insert, (row['Aglomerado'], row['Año'], row['Fecha'], row['Semestre'], row['Cobertura'], row['Quintil'],
                                row['Si consulto'], row['No consulto']))
            conn.commit()
            df_datos_nuevos['Fecha'] = pd.to_datetime(df_datos_nuevos['Fecha'], format='%Y-%m-%d')

        else: 
            print("Se verifico la tabla de IPICORR")
            
        cursor.close()
        conn.close()