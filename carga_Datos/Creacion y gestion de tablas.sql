USE prueba1;
-- Tabla de provincias
CREATE TABLE Provincias(
id_provincia_indec int primary key not null,
nombre_provincia_indec varchar(20)
);

Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (2, 'CABA');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (6, 'Buenos Aires');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (10, 'Catamarca');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (14, 'Cordoba');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (18, 'Corrientes');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (22, 'Chaco');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (23, 'Chubut');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (30, 'Entre Rios');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (34, 'Formosa');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (38, 'Jujuy');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (42, 'La Pampa');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (46, 'La Rioja');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (50, 'Mendoza');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (54, 'Misiones');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (58, 'Neuquen');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (62, 'Rio Negro');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (66, 'Salta');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (70, 'San Juan');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (74, 'San Luis');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (78, 'Santa Cruz');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (82, 'Santa Fe');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (86, 'Santiago Del Estero');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (90, 'Tucuman');
Insert into Provincias(id_provincia_indec, nombre_provincia_indec) Values (94, 'Tierra Del Fuego');

Select * from Provincias;

-- Tabla de Localidades
Select * from localidades;

-- Unions Provincias y localidades
SELECT provincias.nombre_provincia_indec AS provincia, localidades.nombre_departamento_indec AS localidad, localidades.codigo_departamento_indec AS codigo_departamento_indec
FROM localidades
JOIN provincias ON localidades.id_provincia_indec = provincias.id_provincia_indec;

-- Tabla con los puestos de trabajo  
Select COUNT(*)  from puestos_trabajo_asalariado;
Select * from puestos_trabajo_asalariado limit 3000;
SELECT * FROM puestos_trabajo_asalariado WHERE codigo_departamento_indec IS NULL;

-- Tabla de clae2(Sectores de actividad)
CREATE TABLE Sectores_de_actividad (
  clae2 INT PRIMARY KEY,
  clae2_desc VARCHAR(255)
);

INSERT INTO Sectores_de_actividad (clae2, clae2_desc)
VALUES
(1, 'Agricultura, ganadería, caza y servicios relacionados'),
(2, 'Silvicultura y explotación forestal'),
(3, 'Pesca y acuicultura'),
(5, 'Extracción de carbón y lignito'),
(6, 'Extracción de petróleo crudo y gas natural'),
(7, 'Extracción de minerales metálicos'),
(8, 'Extracción de otros minerales'),
(9, 'Actividades de apoyo al petróleo y la minería'),
(10, 'Elaboración de productos alimenticios'),
(11, 'Elaboración de bebidas'),
(12, 'Elaboración de productos de tabaco'),
(13, 'Elaboración de productos textiles'),
(14, 'Elaboración de prendas de vestir'),
(15, 'Elaboración de productos de cuero y calzado'),
(16, 'Elaboración de productos de madera'),
(17, 'Elaboración de productos de papel'),
(18, 'Imprentas y editoriales'),
(19, 'Fabricación de productos de refinación de petróleo'),
(20, 'Fabricación de sustancias químicas'),
(21, 'Elaboracion de productos farmacéuticos'),
(22, 'Fabricación de productos de caucho y vidrio'),
(23, 'Fabricación de productos de vidrio y otros minerales no metálicos'),
(24, 'Fabricación de metales comunes'),
(25, 'Fabricación de productos elaborados del metal, excepto maquinaria y equipo'),
(26, 'Fabricación de productos de informática, de electrónica y de óptica'),
(27, 'Fabricación de equipo eléctrico'),
(28, 'Fabricación de maquinarias'),
(29, 'Fabricación de vehículos automotores, remolques y semirremolques'),
(30, 'Fabricación de otros equipos de transporte'),
(31, 'Fabricación de muebles'),
(32, 'Otras industrias manufactureras'),
(33, 'Reparación e instalación de maquinaria y equipo'),
(35, 'Suministro de electricidad, gas, vapor y aire acondicionado'),
(36, 'Captación, tratamiento y distribución de agua'),
(37, 'Evacuación de aguas residuales'),
(38, 'Recogida, tratamiento y eliminación de desechos'),
(39, 'Descontaminación y otros servicios'),
(41, 'Construcción de edificios y partes'),
(42, 'Obras de ingeniería civil'),
(43, 'Actividades especializadas de construcción'),
(45, 'Comercio al por mayor y al por menor y reparación de vehículos automotores y motos'),
(46, 'Comercio al por mayor excepto autos y motos'),
(47, 'Comercio al por menor excepto autos y motos'),
(49, 'Transporte terrestre y por tuberías'),
(50, 'Transporte acuático'),
(51, 'Transporte aéreo'),
(52, 'Almacenamiento y actividades de apoyo al transporte'),
(53, 'Servicio de correo y mensajería'),
(55, 'Servicios de alojamiento'),
(56, 'Servicios de expendio de alimentos y bebidas'),
(58, 'Edición'),
(59, 'Servicios audiovisuales'),
(60, 'Programación y transmisiones de TV y radio'),
(61, 'Telecomunicaciones'),
(62, 'Servicios de programación, consultoría informática y actividades conexas'),
(63, 'Actividades de procesamiento de información'),
(64, 'Servicios financieros (excepto seguros y pensiones)'),
(65, 'Servicios de seguros, reaseguros y pensiones'),
(66, 'Servicios auxiliares de la actividad financiera y de seguros'),
(68, 'Servicios inmobiliarios'),
(69, 'Servicios jurídicos y de contabilidad'),
(70, 'Servicios y asesoramiento de dirección y gestión empresarial'),
(71, 'Servicios de arquitectura e ingeniería'),
(72, 'Investigación y desarrollo científico'),
(73, 'Servicios de publicidad e investigación de mercado'),
(74, 'Otras actividades profesionales, científicas y técnicas'),
(75, 'Servicios veterinarios'),
(77, 'Alquiler y arrendamiento'),
(78, 'Servicios de obtención y dotación de personal'),
(79, 'Agencias de viajes, servicios de reservas y actividades conexas'),
(80, 'Actividades de investigación y seguridad'),
(81, 'Servicios a edificios y actividades de jardinería'),
(82, 'Actividades administrativas y de apoyo a oficinas y empresas'),
(84, 'Administración pública, defensa y seguridad social'),
(85, 'Enseñanza'),
(86, 'Servicios de salud humana'),
(87, 'Actividades de atención en instituciones'),
(88, 'Actividades de atención sin alojamiento'),
(90, 'Servicios artísticos y de espectáculos'),
(91, 'Servicios de bibliotecas, archivos y museos y servicios culturales n.c.p.'),
(92, 'Juegos de azar y apuestas'),
(93, 'Actividades deportivas, recreativas y de entretenimiento'),
(94, 'Servicios de asociaciones'),
(95, 'Reparación de computadoras y equipos de uso doméstico'),
(96, 'Otros servicios personales'),
(999, 'Otros sectores');

-- Union de tablas 
SELECT provincias.nombre_provincia_indec AS provincia, 
       localidades.nombre_departamento_indec AS localidad, 
       puestos_trabajo_asalariado.fecha AS fecha,
       sectores_de_actividad.clae2_desc AS sector_de_actividad,
       puestos_trabajo_asalariado.puestos AS puestos
FROM localidades
JOIN provincias ON localidades.id_provincia_indec = provincias.id_provincia_indec
JOIN puestos_trabajo_asalariado ON localidades.codigo_departamento_indec = puestos_trabajo_asalariado.codigo_departamento_indec
JOIN sectores_de_actividad ON puestos_trabajo_asalariado.clae2 = sectores_de_actividad.clae2
LIMIT 0, 30000;

-- Tabla de IPC del NEA
-- Creacion de la tabla
CREATE TABLE IPC_regionNEA(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);

-- Ver los datos de la tabla IPC_regionNEA
SELECT * FROM prueba1.ipc_regionnea;
Select * from prueba1.ipc_regionnea limit 10;

-- Tabla Nacional
CREATE TABLE IPC_TotalNacion(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);

SELECT * FROM prueba1.ipc_totalnacion;

-- Tabla Region GBA
CREATE TABLE IPC_RegionGBA(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);

SELECT * FROM prueba1.ipc_regiongba;

-- Tabla Region Pampeana
CREATE TABLE IPC_RegionPampeana(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);

SELECT * FROM prueba1.ipc_regionpampeana;

-- Tabla Region Noroeste
CREATE TABLE IPC_RegionNoroeste(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);

SELECT * FROM prueba1.ipc_regionnoroeste;

-- Tabla Region Cuyo
CREATE TABLE IPC_RegionCuyo(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);

SELECT * FROM prueba1.ipc_regioncuyo;

-- Tabla Region Patagonia
CREATE TABLE IPC_RegionPatagonia(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);

SELECT * FROM prueba1.ipc_regionpatagonia;


-- VARIACION INTERMENSUAL
-- variacion nacion
CREATE TABLE variacion_intermensual_nacion(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion nea
CREATE TABLE variacion_intermensual_nea(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion patagonia
CREATE TABLE variacion_intermensual_patagonia(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion pampeana
CREATE TABLE variacion_intermensual_pampeana(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion noroeste
CREATE TABLE variacion_intermensual_noroeste(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion gba
CREATE TABLE variacion_intermensual_gba(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion Cuyo
CREATE TABLE variacion_intermensual_cuyo(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);


-- VARIACION INTERANUAL
-- variacion nacion
CREATE TABLE variacion_intermensual_nacion(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion nea
CREATE TABLE variacion_intermensual_nea(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion patagonia
CREATE TABLE variacion_intermensual_patagonia(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion pampeana
CREATE TABLE variacion_intermensual_pampeana(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion noroeste
CREATE TABLE variacion_intermensual_noroeste(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion gba
CREATE TABLE variacion_intermensual_gba(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);
-- variacion Cuyo
CREATE TABLE variacion_intermensual_cuyo(
Fecha date not null,
Nivel_General float,
Alimentos_y_bebidas_no_alcoholicas float,
Bebidas_alcoholicas_y_tabaco float,
Prendas_de_vestir_y_calzado float,
Vivienda_agua_electricidad_gas_y_otros_combustibles float,
Equipamiento_y_mantenimiento_del_hogar float,
Salud float,
Transporte float,
Comunicación float,
Recreación_y_cultura float,
Educación float,
Restaurantes_y_hoteles float,
Bienes_y_servicios_varios float
);