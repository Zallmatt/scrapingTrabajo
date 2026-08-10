from pymysql import connect
from sqlalchemy import create_engine, text
import pandas as pd

class conexionBaseDatos:

    #Valores de atributos
    def __init__(self, host, user, password, database):

        self.host = host
        self.user = user
        self.password = password
        self.database = database

        #Atributos que manejan la BDD para validaciones
        self.conn = None
        self.cursor = None

        #Create engine para hacer carga directa
        self.engine = create_engine(f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{3306}/{self.database}")




    #Objetivo: Conectar la BDD

    def conectar_bdd(self):
        self.conn = connect(
            host = self.host, user = self.user, password = self.password, database = self.database
        )
        self.cursor = self.conn.cursor()

        return self
    
    def cargaBaseDatos(self, df):
        print("\n*****************************************************************************")
        print("***********************Inicio de REM precios minoristas************************")
        print("\n*****************************************************************************")
        # Suponiendo que 'df' es tu DataFram
        print(df)
        query_delete = 'TRUNCATE rem_precios_minoristas'
        self.cursor.execute(query_delete)
        #Cargamos los datos usando una query y el conector. Ejecutamos las consultas
        engine = create_engine(f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{3306}/{self.database}")
       
    
        df.to_sql(name="rem_precios_minoristas", con=engine, if_exists='replace', index=False)
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE rem_precios_minoristas ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
        except Exception as e:
            print(f"Error al agregar columna updated_at: {e}")

        
    def cargaBaseDatos2(self, df):
        print("\n*****************************************************************************")
        print("*************************Inicio de REM cambio nominal**************************")
        print("\n*****************************************************************************")
        # Suponiendo que 'df' es tu DataFram
        print(df)
        query_delete = 'TRUNCATE rem_cambio_nominal'
        self.cursor.execute(query_delete)
        #Cargamos los datos usando una query y el conector. Ejecutamos las consultas
        engine = create_engine(f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{3306}/{self.database}")
       
    
        df.to_sql(name="rem_cambio_nominal", con=engine, if_exists='replace', index=False)
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE rem_cambio_nominal ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
        except Exception as e:
            print(f"Error al agregar columna updated_at: {e}")

        
        # Confirmar los cambios en la base de datos
        self.conn.commit()
        # Cerrar el cursor y la conexión
        self.cursor.close()
        self.conn.close()


    # ======== ZONA DE LOS PRECIOS MINORISTAS ======== #

    #Comparar las cantidades de datos del IPC MINORISTA
    def validar_carga_ipc_minorista(self):
        
        #Busqueda del dato
        df_bdd = pd.read_sql('SELECT * FROM ipc_rem_variaciones',self.conn)

        #Retornamos el tamaño
        return len(df_bdd)


    #Objetivo: Realizar o NO, la carga de los datos del REM correspondiente al IPC MINORISTA
    def load_precios_minoristas(self,df_rem_precios_minoristas):
        
        #tamanos del dataframe, y de la cantidad de datos que hay en la bdd
        tamano_df = len(df_rem_precios_minoristas)
        tamano_bdd = self.validar_carga_ipc_minorista()
        
        #Si existen datos nuevos --> CARGAR
        if tamano_df > tamano_bdd:

            #Buscamos solo los datos nuevos.
            df_tail = df_rem_precios_minoristas.tail(tamano_df - tamano_bdd)
            df_tail.to_sql(name = "ipc_rem_variaciones",con = self.engine,if_exists='append',index = False) #--> Carga final
            try:
                with self.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE ipc_rem_variaciones ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
            except Exception as e:
                print(f"Error al agregar columna updated_at: {e}")

            print("************************************************************************")
            print("** SE HA PRODUCIDO UNA ACTUALIZACION IPC REM DE PRECIOS MINORISTAS **")
            print("************************************************************************")

        #Si NO existen datos nuevos --> NO CARGAR
        else:
            print("** NO EXISTEN DATOS NUEVOS A CARGAR PARA IPC REM DE PRECIOS MINORISTAS **")
    


        # ======== ZONA DE LOS CAMBIOS NOMINALES ======== #


    #Comparar las cantidades de datos de LOS CAMBIOS NOMINALES
    def validar_carga_cambio_nominal(self):
        
        #Busqueda del dato
        df_bdd = pd.read_sql('SELECT * FROM rem_cambio_nominal',self.conn)

        #Retornamos el tamaño
        return len(df_bdd)
    

    #Objetivo: Realizar o NO, la carga de los datos del REM correspondiente al CAMBIO NOMINAL DEL DOLAR
    def load_cambio_nominal(self,df_rem_cambio_nominal):
        
        #tamanos del dataframe, y de la cantidad de datos que hay en la bdd
        tamano_df = len(df_rem_cambio_nominal)
        tamano_bdd = self.validar_carga_cambio_nominal()
        
        #Si existen datos nuevos --> CARGAR
        if tamano_df > tamano_bdd:

            #Buscamos solo los datos nuevos.
            df_tail = df_rem_cambio_nominal.tail(tamano_df - tamano_bdd)
            df_tail.to_sql(name = "rem_cambio_nominal",con = self.engine,if_exists='append',index = False) #--> Carga final
            try:
                with self.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE rem_cambio_nominal ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"))
            except Exception as e:
                print(f"Error al agregar columna updated_at: {e}")

            print("************************************************************************")
            print("** SE HA PRODUCIDO UNA ACTUALIZACION EN LOS CAMBIOS NOMINALES DEL REM **")
            print("************************************************************************")

        #Si NO existen datos nuevos --> NO CARGAR
        else:
            print("** NO EXISTEN DATOS NUEVOS A CARGAR PARA LOS CAMBIOS NOMINALES DEL REM **")
    

    #MAIN DE OPERACIONES 
    def main(self,df_rem_precios_minoristas, df_rem_cambio_nominal):
        

        #Conectar a la BDD
        self.conectar_bdd()

        #Carga de las tablas
        self.load_precios_minoristas(df_rem_precios_minoristas)
        self.load_cambio_nominal(df_rem_cambio_nominal)

        #Cierre de la conexiones
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

