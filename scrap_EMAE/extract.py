import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
import os
import urllib3

class HomePage:


    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


    options = webdriver.ChromeOptions()
    options.add_argument('--headless')

    # Configuración del navegador (en este ejemplo, se utiliza ChromeDriver)
    driver = webdriver.Chrome(options=options)  # Reemplaza con la ubicación de tu ChromeDriver

    # URL de la página que deseas obtener
    url_pagina = 'https://www.indec.gob.ar/indec/web/Nivel4-Tema-3-9-48'

    # Cargar la página web
    driver.get(url_pagina)

    wait = WebDriverWait(driver, 10)

    # Encontrar el enlace al archivo
    archivo = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[1]/div[2]/div[4]/div[1]/div[2]/div/div/div/div/a[2]")))

    # Obtener la URL del archivo
    url_archivo = archivo.get_attribute('href')
    # Imprimir la URL del archivo
    print(url_archivo)
    
    # Ruta de la carpeta donde guardar el archivo
    # Obtener la ruta del directorio actual (donde se encuentra el script)
    directorio_actual = os.path.dirname(os.path.abspath(__file__))

    # Construir la ruta de la carpeta "files" dentro del directorio actual
    carpeta_guardado = os.path.join(directorio_actual, 'files')

    # Nombre del archivo
    nombre_archivo = 'EMAE.xls'

    # Descargar el archivo
    response = requests.get(url_archivo)

    # Guardar el archivo en la carpeta especificada
    ruta_guardado = f'{carpeta_guardado}\\{nombre_archivo}'
    with open(ruta_guardado, 'wb') as file:
        file.write(response.content)

    #Segundo archivo
    # Encontrar el enlace al segundo archivo
    archivo_2 = wait.until(EC.presence_of_element_located((By.XPATH, "/html/body/div[2]/div[1]/div[2]/div[4]/div[1]/div[2]/div/div/div/div/a[1]"))) 
    # Obtener la URL del segundo archivo
    url_archivo_2 = archivo_2.get_attribute('href')
    # Imprimir la URL del segundo archivo
    print(url_archivo_2)

    # Nombre del segundo archivo
    nombre_archivo_2 = 'EMAEVAR.xls'  # Reemplaza con el nombre deseado para el segundo archivo

    # Descargar el segundo archivo
    response_2 = requests.get(url_archivo_2)

    # Guardar el segundo archivo en la carpeta especificada
    ruta_guardado_2 = f'{carpeta_guardado}\\{nombre_archivo_2}'
    with open(ruta_guardado_2, 'wb') as file:
        file.write(response_2.content)

    # Cerrar el navegador
    driver.quit()
