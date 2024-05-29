import mysql.connector
import pandas as pd

class LoadDataBaseMedicos:
    def __init__(self, host, user, password, database):
        self.host = host
        self.user = user
        self.password = password
        self.database = database
        self.conn = None
        self.cursor = None

    def conectar_bdd(self):
        self.conn = mysql.connector.connect(
            host=self.host, user=self.user, password=self.password, database=self.database
        )
        self.cursor = self.conn.cursor()
        return self

    def loadDataBaseMedicos(self):
        query = "SELECT * FROM siso_ctes.v_estadisticas"
        df = pd.read_sql(query, con=self.conn)
        return df

    def cerrar_conexion(self):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
