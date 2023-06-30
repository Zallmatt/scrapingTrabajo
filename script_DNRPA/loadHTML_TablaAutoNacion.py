import datetime
from bs4 import BeautifulSoup
import mysql.connector
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.select import Select
import time
from tabulate import tabulate


host = 'localhost'
user = 'root'
password = 'Estadistica123'
database = 'prueba1'

class loadHTML_TablaAutoNacion:
    def loadInDataBase(self, host, user, password, database):
        # Se toma el tiempo de comienzo
        start_time = time.time()

        # Establecer la conexión a la base de datos
        conn = mysql.connector.connect(
            host=host, user=user, password=password, database=database
        )
        # Crear el cursor para ejecutar consultas
        cursor = conn.cursor()
        try:
            driver = webdriver.Chrome()
            driver.get('https://www.dnrpa.gov.ar/portal_dnrpa/estadisticas/rrss_tramites/tram_prov.php?origen=portal_dnrpa&tipo_consulta=inscripciones')

            # Obtener la ventana actual
            ventana_actual = driver.current_window_handle
            
            elemento = driver.find_element(By.XPATH, '//*[@id="seleccion"]/center/table/tbody/tr[2]/td/select')
            # Obtener todas las opciones del elemento select
            opciones = elemento.find_elements(By.TAG_NAME, 'option')

            # Buscar la opción deseada por su valor y hacer clic en ella
            valor_deseado = '2014'  # Valor de la opción que deseas seleccionar

            for opcion in opciones:
                if opcion.get_attribute('value') == valor_deseado:
                    opcion.click()
                    break
            
            boton = driver.find_element(By.XPATH, '//*[@id="seleccion"]/center/table/tbody/tr[4]/td/input[1]')
            boton.click()
            
            time.sleep(5)
            
            boton_aceptar = driver.find_element(By.XPATH, '//*[@id="seleccion"]/center/center/input')
            boton_aceptar.click()
            
            # Esperar un momento para que se abra la nueva pestaña
            driver.implicitly_wait(5)
            # Cambiar al contexto de la nueva pestaña
            for ventana in driver.window_handles:
                if ventana != ventana_actual:
                    driver.switch_to.window(ventana)
            
            time.sleep

            # Encontrar el elemento <div> con la clase 'grid'
            elemento_div = driver.find_element(By.CLASS_NAME, 'grid')

            # Encontrar la tabla dentro del elemento <div>
            elemento_tabla = elemento_div.find_element(By.TAG_NAME, 'table')

            # Obtener todas las filas de la tabla
            filas = elemento_tabla.find_elements(By.TAG_NAME, 'tr')

            # Lista para almacenar los datos de la tabla
            tabla_datos = []

            # Recorrer las filas de la tabla
            for fila in filas:
                # Obtener las celdas de cada fila
                celdas = fila.find_elements(By.TAG_NAME, 'td')
                
                # Lista para almacenar los valores de cada fila
                fila_datos = []
                
                # Obtener el contenido de cada celda y agregarlo a la lista de datos de la fila
                for celda in celdas:
                    fila_datos.append(celda.text)
                
                # Agregar la lista de datos de la fila a la tabla de datos
                tabla_datos.append(fila_datos)


            # Imprimir la tabla en formato de tabla
            print(tabulate(tabla_datos, headers="firstrow"))
            
            
            # Se toma el tiempo de finalización y se calcula
            end_time = time.time()
            duration = end_time - start_time
            print("-----------------------------------------------")
            print("Se guardaron los datos de SIPA NACIONAL CON ESTACIONALIDAD")
            print("Tiempo de ejecución:", duration)

            # Cerrar la conexión a la base de datos
            conn.close()

        except Exception as e:
            # Manejar cualquier excepción ocurrida durante la carga de datos
            print(f"Data Cuyo: Ocurrió un error durante la carga de datos: {str(e)}")
            conn.close()  # Cerrar la conexión en caso de error
            
loadHTML_TablaAutoNacion().loadInDataBase(host, user, password, database)