import mysql.connector
import time

class armadoVariacionIntermensualCuyo:
    def calculoVariacion(self):
        #Se toma el tiempo de comienzo
        start_time = time.time()
        
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='Estadistica123',
            database='prueba1'
        )
        
        # Crear el cursor para ejecutar consultas
        cursor = conn.cursor()

        # Obtener los datos de la tabla original
        select_query = "SELECT Fecha, Nivel_General, Alimentos_y_bebidas_no_alcoholicas, Bebidas_alcoholicas_y_tabaco, Prendas_de_vestir_y_calzado, Vivienda_agua_electricidad_gas_y_otros_combustibles, Equipamiento_y_mantenimiento_del_hogar, Salud, Transporte, Comunicación, Recreación_y_cultura, Educación, Restaurantes_y_hoteles, Bienes_y_servicios_varios FROM ipc_regioncuyo"
        cursor.execute(select_query)
        rows = cursor.fetchall()

        # Obtener las fechas existentes en la tabla variacion_interanual_nacion
        select_dates_query = "SELECT Fecha FROM variacion_interanual_cuyo"
        cursor.execute(select_dates_query)
        existing_dates = [row[0] for row in cursor.fetchall()]

        # Calcular las variaciones y guardarlas en la tabla existente
        for i in range(1, len(rows)):
            fecha_actual, nivel_general_actual, alimentos_bebidas_actual, bebidas_alcoholicas_actual, prendas_vestir_actual, vivienda_actual, equipamiento_actual, salud_actual, transporte_actual, comunicacion_actual, recreacion_actual, educacion_actual, restaurantes_actual, bienes_servicios_actual = rows[i]
            fecha_anterior, nivel_general_anterior, alimentos_bebidas_anterior, bebidas_alcoholicas_anterior, prendas_vestir_anterior, vivienda_anterior, equipamiento_anterior, salud_anterior, transporte_anterior, comunicacion_anterior, recreacion_anterior, educacion_anterior, restaurantes_anterior, bienes_servicios_anterior = rows[i - 1]
            variacion_general = ((nivel_general_actual / nivel_general_anterior) - 1) * 100
            variacion_alimentos_bebidas = ((alimentos_bebidas_actual / alimentos_bebidas_anterior) - 1) * 100
            variacion_bebidas_alcoholicas = ((bebidas_alcoholicas_actual / bebidas_alcoholicas_anterior) - 1) * 100
            variacion_prendas_vestir = ((prendas_vestir_actual / prendas_vestir_anterior) - 1) * 100
            variacion_vivienda = ((vivienda_actual / vivienda_anterior) - 1) * 100
            variacion_equipamiento = ((equipamiento_actual / equipamiento_anterior) - 1) * 100
            variacion_salud = ((salud_actual / salud_anterior) - 1) * 100
            variacion_transporte = ((transporte_actual / transporte_anterior) - 1) * 100
            variacion_comunicacion = ((comunicacion_actual / comunicacion_anterior) - 1) * 100
            variacion_recreacion = ((recreacion_actual / recreacion_anterior) - 1) * 100
            variacion_educacion = ((educacion_actual / educacion_anterior) - 1) * 100
            variacion_restaurantes = ((restaurantes_actual / restaurantes_anterior) - 1) * 100
            variacion_bienes_servicios = ((bienes_servicios_actual / bienes_servicios_anterior) - 1) * 100

            # Verificar si la fecha actual ya existe en la tabla variacion_interanual_nacion
            if fecha_actual not in existing_dates:
                # Insertar una nueva fila con la fecha y las variaciones calculadas
                insert_query = "INSERT INTO variacion_interanual_cuyo (Fecha, Nivel_General, Alimentos_y_bebidas_no_alcoholicas, Bebidas_alcoholicas_y_tabaco, Prendas_de_vestir_y_calzado, Vivienda_agua_electricidad_gas_y_otros_combustibles, Equipamiento_y_mantenimiento_del_hogar, Salud, Transporte, Comunicación, Recreación_y_cultura, Educación, Restaurantes_y_hoteles, Bienes_y_servicios_varios) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                insert_values = (
                    fecha_actual,
                    variacion_general,
                    variacion_alimentos_bebidas,
                    variacion_bebidas_alcoholicas,
                    variacion_prendas_vestir,
                    variacion_vivienda,
                    variacion_equipamiento,
                    variacion_salud,
                    variacion_transporte,
                    variacion_comunicacion,
                    variacion_recreacion,
                    variacion_educacion,
                    variacion_restaurantes,
                    variacion_bienes_servicios
                )
                cursor.execute(insert_query, insert_values)
                existing_dates.append(fecha_actual)  # Agregar la fecha a la lista de fechas existentes

            else:
                # Actualizar los valores de variación en la fila existente
                update_query = "UPDATE variacion_interanual_cuyo SET Nivel_General = %s, Alimentos_y_bebidas_no_alcoholicas = %s, Bebidas_alcoholicas_y_tabaco = %s, Prendas_de_vestir_y_calzado = %s, Vivienda_agua_electricidad_gas_y_otros_combustibles = %s, Equipamiento_y_mantenimiento_del_hogar = %s, Salud = %s, Transporte = %s, Comunicación = %s, Recreación_y_cultura = %s, Educación = %s, Restaurantes_y_hoteles = %s, Bienes_y_servicios_varios = %s WHERE Fecha = %s"
                update_values = (
                    variacion_general,
                    variacion_alimentos_bebidas,
                    variacion_bebidas_alcoholicas,
                    variacion_prendas_vestir,
                    variacion_vivienda,
                    variacion_equipamiento,
                    variacion_salud,
                    variacion_transporte,
                    variacion_comunicacion,
                    variacion_recreacion,
                    variacion_educacion,
                    variacion_restaurantes,
                    variacion_bienes_servicios,
                    fecha_actual
                )
                cursor.execute(update_query, update_values)

        # Confirmar los cambios y cerrar el cursor y la conexión
        conn.commit()
        cursor.close()
        conn.close()
        
        # Calcular y mostrar el tiempo de ejecución
        end_time = time.time()
        execution_time = end_time - start_time
        print("Tiempo de ejecución de Cuyo:", execution_time)