import mysql.connector
import numpy as np
import pandas as pd
import time
import os
from email.message import EmailMessage
import ssl
import smtplib

nuevos_datos = []
    
class loadCSVData_SP:
    def loadInDataBase(self, host, user, password, database):
        #Se toma el tiempo de comienzo
        start_time = time.time()
        
        # Establecer la conexión a la base de datos
        conn = mysql.connector.connect(
            host=host, user=user, password=password, database=database
        )

        cursor = conn.cursor()
        
        # Nombre de la tabla en MySQL
        table_name = 'DP_salarios_sector_privado'
        # Obtener la ruta del directorio actual (donde se encuentra el script)
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        # Construir la ruta de la carpeta "files" dentro del directorio actual
        ruta_carpeta_files = os.path.join(directorio_actual, 'files')
        file_name = "salarioPromedioSP.csv"
        # Construir la ruta completa del archivo CSV dentro de la carpeta "files"
        file_path = os.path.join(ruta_carpeta_files, file_name)
                
        # Leer el archivo de csv y hacer transformaciones
        df = pd.read_csv(file_path)  # Leer el archivo CSV y crear el DataFrame
        df = df.replace({np.nan: None})  # Reemplazar los valores NaN(Not a Number) por None

        print("columnas -- ", df.columns)

        # Aplicar strip() al nombre de la columna antes de acceder a ella
        column_name = ' w_mean '  # Nombre de la columna con espacios en blanco
        column_name_stripped = column_name.strip()  # Eliminar espacios en blanco

        # Verificar si la columna existe en el DataFrame
        if column_name_stripped in df.columns:
            # Realizar transformaciones en el DataFrame utilizando el nombre de columna sin espacios
            df.loc[df[column_name_stripped] < 0, column_name_stripped] = 0 #Los datos <0 se reempalazan a 0
        else:
            print(f"La columna '{column_name_stripped}' no existe en el DataFrame.")
        
        #↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓CARGA EN BASE DE DATOS ↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓↓
        print("Tabla de Salarios Sector Privado")
        #Verificar cantidad de filas anteriores 
        select_row_count_query = "SELECT COUNT(*) FROM DP_salarios_sector_privado"
        cursor.execute(select_row_count_query)
        row_count_before = cursor.fetchone()[0]
        
        delete_query ="TRUNCATE `prueba1`.`DP_salarios_sector_privado`"
        cursor.execute(delete_query)
        
        insert_query = f"INSERT INTO {table_name} VALUES ({', '.join(['%s' for _ in range(len(df.columns))])})"
        
        for index, row in df.iterrows():
            data_tuple = tuple(row)
        
            # Si los valores no existen, realizar la inserción
            conn.cursor().execute(insert_query, data_tuple)
            print(data_tuple)
            
            # Agregar los datos nuevos a la lista
            nuevos_datos.append(data_tuple)
            
        cursor.execute(select_row_count_query)
        row_count_after = cursor.fetchone()[0]
        
        #Comparar la cantidad de antes y despues
        if row_count_after > row_count_before:
            print("Se agregaron nuevos datos")
            enviar_correo()   
        else:
            print("Se realizo una verificacion de la base de datos")
            
        
        conn.commit()
            
        print("====================================================================")
        print("Se realizo la actualizacion de la tabla de Salarios Sector Privado")
        print("====================================================================")

        #Se toma el tiempo de finalizacion y se calcula
        end_time = time.time()
        duration = end_time - start_time
        print(f"Tiempo de ejecución: {duration} segundos")
        
        # Cerrar la conexión a la base de datos
        conn.close()
        
        
def enviar_correo():
    email_emisor='departamientoactualizaciondato@gmail.com'
    email_contraseña = 'cmxddbshnjqfehka'
    email_receptor = ['matizalazar2001@gmail.com','gastongrillo2001@gmail.com']
    asunto = 'Modificación en la base de datos'
    mensaje = 'Se ha producido una modificación en la base de datos.Tabla de Salarios Sector Privado'
    body = "Se han agregado nuevos datos:\n\n"
    for data in nuevos_datos:
        body += ', '.join(map(str, data)) + '\n'
    
    em = EmailMessage()
    em['From'] = email_emisor
    em['To'] = email_receptor
    em['Subject'] = asunto
    em.set_content(mensaje)
    
    contexto= ssl.create_default_context()
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=contexto) as smtp:
        smtp.login(email_emisor, email_contraseña)
        smtp.sendmail(email_emisor, email_receptor, em.as_string())