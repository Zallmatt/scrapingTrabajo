from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import pandas as pd



class readSheets:
    def leer_datos_tasas(self):
        df = []
        # Define los alcances y la ruta al archivo JSON de credenciales
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

        directorio_desagregado = os.path.dirname(os.path.abspath(__file__))
        ruta_carpeta_files = os.path.join(directorio_desagregado, 'files')
        KEY = os.path.join(ruta_carpeta_files, 'key.json')

        # Escribe aquí el ID de tu documento:
        SPREADSHEET_ID = '1BHEd_y02Lwjej_2Rkr_HYO7ZU4Y6m2gHEG4uPm0b5Go'

        # Carga las credenciales desde el archivo JSON
        creds = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES)

        # Crea una instancia de la API de Google Sheets
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets()

        # Realiza una llamada a la API para obtener datos desde la hoja 'Hoja 1' en el rango 'A1:A8'
        result = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='datos trimestrales!A:C').execute()

        # Extrae los valores del resultado
        values = result.get('values', [])[1:]

        # Crea el DataFrame df1
        df1 = pd.DataFrame(values, columns=['Fecha', 'Trimestre', 'Aglomerado'])

        # Realiza una llamada a la API para obtener datos desde la hoja 'Hoja 1' en el rango 'I1:L8'
        result2 = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='datos trimestrales!I:L').execute()

        # Extrae los valores del resultado
        values2 = result2.get('values', [])[1:]

        # Crea el DataFrame df2
        df2 = pd.DataFrame(values2, columns=['Tasa de empleo', 'Tasa de desocupación', 'Tasa de actividad', 'Tasa de inactividad'])

        # Unir los dos DataFrames
        # Realiza una llamada a la API para obtener datos desde la hoja 'Hoja 1' en el rango 'I1:L8'
        result3 = sheet.values().get(spreadsheetId=SPREADSHEET_ID, range='datos trimestrales!AY:AY').execute()

        # Extrae los valores del resultado
        values3 = result3.get('values', [])[1:]
        # Crea el DataFrame df2
        df3 = pd.DataFrame(values3, columns=['Estado'])

        df = pd.concat([df1, df2, df3], axis=1)
        # Imprimir el DataFrame resultante
        print(df)
        longitud_primera_fila = len(df.iloc[0])
        # Retornar el DataFrame
        if longitud_primera_fila == 8:
            df = df.drop(df.columns[-1], axis=1)
            print(df)
            return df