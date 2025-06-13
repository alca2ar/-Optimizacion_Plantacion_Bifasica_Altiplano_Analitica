import os
import sys

# --- Determinar la ruta base de la aplicación ---
if getattr(sys, 'frozen', False):
    # Si la aplicación se ejecuta como un paquete congelado (ej. PyInstaller)
    application_path = os.path.dirname(sys.executable)
else:
    # Si la aplicación se ejecuta como un script normal .py
    application_path = os.path.dirname(os.path.abspath(__file__))

# --- Definir las rutas base para datos de entrada y salida ---
BASE_DATA_INPUT_PATH = os.path.join(application_path, "data")
BASE_OUTPUT_PATH = os.path.join(application_path, "outputs")

# --- INICIO DEL BLOQUE FALTANTE ---
# --- Rutas comunes a todos los escenarios ---
rutas_comunes = {
    'Coordenadas Nodos': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosReal', 'Coord_nodo.csv'),
    'Mapa': os.path.join(application_path, 'data', 'imgs', 'mapa.png'),
    'Icono Camion': os.path.join(application_path, 'data', 'imgs', 'mionca.png')
}
# --- FIN DEL BLOQUE FALTANTE ---


# --- Diccionario con rutas específicas por escenario ---
# (Nota que las rutas de coordenadas, mapa, etc., ya no están aquí)
rutas_escenarios = {
    'DemandaAlta': {
        'Areas Poligonos': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaAlta', 'areas_poligonos_AD.csv'),
        'Costos Unitarios': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaAlta', 'costos_unitarios_AD.csv'),
        'Datos Especies': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaAlta', 'datos_especies_AD.csv'),
        'Disponibilidad Especies': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaAlta', 'disponibilidad_especies_AD.csv'),
        'Matriz de Distancia VRP': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaAlta', 'dist_matrix_vrp_AD.csv'),
        'Parametros Generales': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaAlta', 'parametros_generales_AD.csv'),
        'Vehiculos VRP': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaAlta', 'vehiculos_vrp_AD.csv')
    },
    'DemandaBaja': {
        'Areas Poligonos': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaBaja', 'areas_poligonos_BD.csv'),
        'Costos Unitarios': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaBaja', 'costos_unitarios_BD.csv'),
        'Datos Especies': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaBaja', 'datos_especies_BD.csv'),
        'Disponibilidad Especies': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaBaja', 'disponibilidad_especies_BD.csv'),
        'Matriz de Distancia VRP': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaBaja', 'dist_matrix_vrp_BD.csv'),
        'Parametros Generales': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaBaja', 'parametros_generales_BD.csv'),
        'Vehiculos VRP': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaBaja', 'vehiculos_vrp_BD.csv')
    },
    'DemandaEquilibrada': {
        'Areas Poligonos': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaEquilibrada', 'areas_poligonos_ED.csv'),
        'Costos Unitarios': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaEquilibrada', 'costos_unitarios_ED.csv'),
        'Datos Especies': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaEquilibrada', 'datos_especies_ED.csv'),
        'Disponibilidad Especies': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaEquilibrada', 'disponibilidad_especies_ED.csv'),
        'Matriz de Distancia VRP': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaEquilibrada', 'dist_matrix_vrp_ED.csv'),
        'Parametros Generales': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaEquilibrada', 'parametros_generales_ED.csv'),
        'Vehiculos VRP': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaEquilibrada', 'vehiculos_vrp_ED.csv')
    },
    'Real_Custom': {
        'Areas Poligonos': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosReal', 'areas_poligonos.csv'),
        'Costos Unitarios': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosReal', 'costos_unitarios.csv'),
        'Datos Especies': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosReal', 'datos_especies.csv'),
        'Disponibilidad Especies': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosReal', 'disponibilidad_especies.csv'),
        'Matriz de Distancia VRP': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosReal', 'dist_matrix_vrp.csv'),
        'Parametros Generales': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosReal', 'parametros_generales.csv'),
        'Vehiculos VRP': os.path.join(BASE_DATA_INPUT_PATH, 'Parametros_Opti', 'CasosReal', 'vehiculos_vrp.csv')
    }
}

# --- Rutas de Guardado de Outputs ---
rutas_outputs = {
    'DemandaAlta': os.path.join(BASE_OUTPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaAlta', 'Outputs'),
    'DemandaBaja': os.path.join(BASE_OUTPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaBaja', 'Outputs'),
    'DemandaEquilibrada': os.path.join(BASE_OUTPUT_PATH, 'Parametros_Opti', 'CasosPrueba', 'DemandaEquilibrada', 'Outputs'),
    'Real_Custom': os.path.join(BASE_OUTPUT_PATH, 'Parametros_Opti', 'CasosReal', 'Outputs')
}