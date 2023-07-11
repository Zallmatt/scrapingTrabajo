import requests
import os
from datetime import datetime
import urllib3
from pathlib import Path

class FileManager:
    
    url = ""
    folder = str(Path.cwd()) + "/scrap_PuestosTrabajoSP/files"#path.cdw toma la ruta actual de trabajo//Se le agrega la carpeta en donde se va a guardad

    def __init__(self, url): #Inicializar los atributos del objeto que creamos.
        self.url = url #Esto permite proporcionar la URL al crear una instancia de la clase.

    def downloadCSV(self):

        urllib3.disable_warnings() #Se desactivan las advertencias de verificación de certificados SSL
        response = requests.get(self.url, verify=False) #Se realiza una solicitud con el get y se guarda en response
        response.raise_for_status()

        if response.status_code == 200:#Se verifica que el codigo sea de exito
            csv_content = response.content #Si es exitoso se guarda el contenido en la variable
            file_name = "trabajoSectorPrivado.csv"  # Nombre personalizado del archivo
            file_path = os.path.join(self.folder, file_name)

            with open(file_path, "wb") as file:#with open lo abre en escritura binaria//El parámetro file_path especifica la ruta completa del archivo que se desea abrir y crear. 
                file.write(csv_content)#Escribe los datos en el archivo

            print("Se guardo el archivo")
            return file_name
        else:
            print("Fallo la desacaga del archivo..")

