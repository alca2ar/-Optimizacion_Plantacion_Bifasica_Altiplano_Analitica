# main_model_runner.py (Versión con Métricas de Rendimiento)

import os
import pandas as pd
from collections import defaultdict
import argparse
import time     # <--- 1. Importamos la librería para medir tiempo
import psutil   # <--- 2. Importamos la librería para medir memoria

# Módulos del proyecto (Versión con OR-Tools)
import config_paths
import data_loader
import model_fase1_ortools as model_fase1
import model_fase2_ortools_milp as model_fase2
import animation_generator


def generate_comparison_outputs(fase1_results, vrp_results, params, output_path):
    """
    Toma los resultados crudos de los solvers y los convierte a los formatos CSV
    esperados para su análisis.
    """
    print("\n--- Iniciando generación de archivos CSV de salida para comparación ---")

    # Asegurarse de que los directorios de salida existan
    fase1_output_dir = os.path.join(output_path, 'Fase1_Suministro_Siembra_Logs', 'Analisis_KPIs_Fase1')
    fase2_output_dir = os.path.join(output_path, 'Fase2_VRP_Logs')
    os.makedirs(fase1_output_dir, exist_ok=True)
    os.makedirs(fase2_output_dir, exist_ok=True)
    
    T = list(range(1, params['T_dias_planificacion'] + 1))
    S = params['S_especies']
    
    # --- Archivo 1: fase1_hectareas_plantadas_diarias.csv ---
    ha_plantadas_data = []
    ha_restantes_total = sum(params['Ha_g_total'].values())
    for t in T:
        ha_plantadas_dia = sum(fase1_results.get('y', {}).get((s, g, t), 0) / params['Dens_s'][s]
                               for s in S for g in params['G_poligonos'])
        ha_restantes_total -= ha_plantadas_dia
        ha_plantadas_data.append({
            'Día': t,
            'Hectareas_Plantadas_Dia': ha_plantadas_dia,
            'Hectareas_Restantes_Total': ha_restantes_total
        })
    df_hectareas = pd.DataFrame(ha_plantadas_data)
    df_hectareas.to_csv(os.path.join(fase1_output_dir, 'fase1_hectareas_plantadas_diarias.csv'), index=False)
    print("Archivo 'fase1_hectareas_plantadas_diarias.csv' generado.")

    # --- Archivo 2: fase1_costos_diarios.csv ---
    costos_data = []
    presupuesto_acumulado = 0
    for t in T:
        gasto_compras_dia = sum(fase1_results.get('x', {}).get((s, p, t), 0) * params['C_sp'].get((s,p), 0)
                                for s in S for p in params['P_proveedores'])
        gasto_desperdicio_dia = sum(fase1_results.get('Desper', {}).get((s, g, t), 0) * params.get('DesperPenalty_s', 1.0)
                                     for s in S for g in params['G_poligonos'])
        presupuesto_acumulado += gasto_compras_dia
        costos_data.append({
            'Día': t,
            'Gasto_Compras_Dia': gasto_compras_dia,
            'Gasto_Desperdicio_Dia': gasto_desperdicio_dia,
            'Presupuesto_Acumulado_Utilizado': presupuesto_acumulado
        })
    df_costos = pd.DataFrame(costos_data)
    df_costos.to_csv(os.path.join(fase1_output_dir, 'fase1_costos_diarios.csv'), index=False)
    print("Archivo 'fase1_costos_diarios.csv' generado.")
    
    # --- Archivo 3: vrp_rutas_resumen.csv ---
    rutas_data = []
    for dia, resultado_dia in vrp_results.items():
        if resultado_dia and resultado_dia.get('rutas'):
            for ruta_info in resultado_dia['rutas']:
                rutas_data.append({
                    'Día': dia,
                    'Vehículo': ruta_info['vehiculo'],
                    'Ruta_Nodos_Str': ' -> '.join(map(str, ruta_info['ruta'])),
                    'Carga_Plantas': 0, # Este dato requeriría más detalle para calcularse
                    'Tiempo_min': resultado_dia.get('tiempo_total', 0)
                })
    df_rutas = pd.DataFrame(rutas_data)
    df_rutas.to_csv(os.path.join(fase2_output_dir, 'vrp_rutas_resumen.csv'), index=False)
    print("Archivo 'vrp_rutas_resumen.csv' generado.")


def run_complete_optimization(scenario_name):
    """
    Función orquestadora principal para el modelo de optimización.
    """
    print(f"--- INICIANDO MODELO DE OPTIMIZACIÓN PARA ESCENARIO: {scenario_name} ---")

    # --- PASO 1: Carga de Configuración y Datos ---
    print("\n--- PASO 1: Cargando datos y parámetros ---")
    
    if scenario_name not in config_paths.rutas_escenarios:
        print(f"Error: El escenario '{scenario_name}' no se encuentra definido en config_paths.py.")
        print(f"Escenarios disponibles: {list(config_paths.rutas_escenarios.keys())}")
        return

    paths = {**config_paths.rutas_comunes, **config_paths.rutas_escenarios[scenario_name]}
    output_path = config_paths.rutas_outputs[scenario_name]
    
    os.makedirs(os.path.join(output_path, 'Fase1_Suministro_Siembra_Logs', 'Analisis_KPIs_Fase1'), exist_ok=True)
    os.makedirs(os.path.join(output_path, 'Fase2_VRP_Logs', 'Analisis_Rutas_Detalladas'), exist_ok=True)
    os.makedirs(os.path.join(output_path, 'Animaciones'), exist_ok=True)

    params = {}
    params.update(data_loader.cargar_parametros_generales(paths["Parametros Generales"]))
    params['S_especies'], params['Dens_s'], params['Area_s'], params['Trat_s'] = data_loader.cargar_datos_especies(paths['Datos Especies'])
    params['P_proveedores'], disp_sp = data_loader.cargar_disponibilidad_y_proveedores(paths['Disponibilidad Especies'])
    params['Disponibilidad_{sp}'] = disp_sp
    params['C_sp'] = data_loader.cargar_costos_unitarios(paths['Costos Unitarios'], params['P_proveedores'])
    params['G_poligonos'], params['Ha_g_total'] = data_loader.cargar_areas_poligonos(paths['Areas Poligonos'])
    params['K_vehiculos_nombres'], params['cap_k_vehiculos_vrp'] = data_loader.cargar_datos_vehiculos_vrp(paths['Vehiculos VRP'])
    
    # Establecer valores por defecto para parámetros clave si no están en el archivo
    params.setdefault('DesperPenalty_s', 1.0)
    params.setdefault('PC_U', params.get('Costo_Unitario_Plantacion_PC', 1.0))
    params.setdefault('StockMinEspecie_s', params.get('Stock_Minimo_Deseado_Por_Especie', 10))

    print("Datos cargados exitosamente.")
    
    # --- PASO 2: Resolver el Modelo de Planificación (Fase 1) ---
    fase1_results = model_fase1.solve_supply_model_gurobi(params, scenario_name)
    
    if not fase1_results:
        print("El modelo de Fase 1 no encontró solución. Finalizando proceso.")
        return

    # --- PASO 3: Resolver el Modelo de Ruteo (Fase 2) para cada día ---
    all_vrp_results = {}
    T = list(range(1, params['T_dias_planificacion'] + 1))

    matriz_tiempos_valores, vrp_nodos_ordenados = data_loader.cargar_matriz_tiempos_vrp(paths["Matriz de Distancia VRP"])
    matriz_tiempos_dict = {}
    for i, nodo_i in enumerate(vrp_nodos_ordenados):
        for j, nodo_j in enumerate(vrp_nodos_ordenados):
            matriz_tiempos_dict[nodo_i, nodo_j] = matriz_tiempos_valores[i][j]

    vehiculos_list = [{'id': f'K{i+1}', 'capacidad': cap} for i, cap in enumerate(params['cap_k_vehiculos_vrp'])]
            
    for t in T:
        demandas_del_dia = defaultdict(float)
        for (s, g, t_res), val in fase1_results.get('y', {}).items():
            if t_res == t:
                demandas_del_dia[g] += val
        
        if not demandas_del_dia:
            print(f"Día {t}: Sin actividad de plantación, se omite el VRP.")
            all_vrp_results[t] = None
            continue

        resultado_vrp_dia = model_fase2.solve_vrp_analytically(
            dia=t,
            demandas_diarias=dict(demandas_del_dia),
            matriz_tiempos=matriz_tiempos_dict,
            vehiculos=vehiculos_list,
            params=params
        )
        all_vrp_results[t] = resultado_vrp_dia

    # --- PASO 4: Generar Archivos de Salida para Comparación ---
    generate_comparison_outputs(fase1_results, all_vrp_results, params, output_path)

    # --- PASO 5: Generar Animaciones ---
    print("\n--- Iniciando generación de animaciones ---")
    ruta_resumen_vrp = os.path.join(output_path, 'Fase2_VRP_Logs', 'vrp_rutas_resumen.csv')
    coords_nodos = data_loader.cargar_coordenadas_nodos(paths["Coordenadas Nodos"])
    map_path = paths['Mapa']
    truck_icon_path = paths['Icono Camion']
    
    if os.path.exists(ruta_resumen_vrp) and coords_nodos:
        df_rutas = pd.read_csv(ruta_resumen_vrp)
        if not df_rutas.empty:
            for dia_animacion in sorted(df_rutas['Día'].unique()):
                rutas_para_gif = df_rutas[df_rutas['Día'] == dia_animacion].to_dict('records')
                animation_generator.create_daily_route_gif(
                    dia_animacion, rutas_para_gif, coords_nodos,
                    map_path, truck_icon_path, os.path.join(output_path, 'Animaciones')
                )
    
    print("\n--- PROCESO DE OPTIMIZACIÓN COMPLETADO ---")


if __name__ == '__main__':
    # --- Configuración de argumentos (sin cambios) ---
    parser = argparse.ArgumentParser(description="Ejecutar el modelo de optimización para un escenario específico.")
    escenarios_disponibles = list(config_paths.rutas_escenarios.keys())
    parser.add_argument(
        "escenario",
        help="El nombre del escenario a resolver.",
        choices=escenarios_disponibles,
        metavar="ESCENARIO"
    )
    args = parser.parse_args()
    
    # ---> 1. INICIAMOS EL CRONÓMETRO <---
    start_time = time.time()
    
    # --- Ejecución principal del modelo (sin cambios) ---
    run_complete_optimization(scenario_name=args.escenario)
    
    # ---> 2. DETENEMOS EL CRONÓMETRO Y CALCULAMOS LA DURACIÓN <---
    end_time = time.time()
    duration_seconds = end_time - start_time
    
    # Convertimos segundos a un formato más legible de minutos y segundos
    mins = int(duration_seconds // 60)
    secs = duration_seconds % 60
    
    # ---> 3. MEDIMOS EL USO DE MEMORIA PICO <---
    # Obtenemos el proceso actual del sistema operativo
    process = psutil.Process(os.getpid())
    # Pedimos la información de memoria en bytes y la convertimos a Megabytes (MB)
    memory_mb = process.memory_info().rss / (1024 * 1024)
    
    # ---> 4. IMPRIMIMOS EL RESUMEN DE RENDIMIENTO AL FINAL DE TODO <---
    print("\n" + "="*50)
    print("  MÉTRICAS DE RENDIMIENTO TOTAL")
    print("="*50)
    print(f"  Tiempo total de ejecución: {mins} minutos y {secs:.2f} segundos.")
    print(f"  Uso de memoria pico: {memory_mb:.2f} MB.")
    print("="*50)
