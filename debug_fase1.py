# debug_fase1_unificado.py

from ortools.linear_solver import pywraplp
import config_paths
import data_loader

def encontrar_conflicto_unificado():
    """
    Versión del script de depuración adaptada para un modelo con un
    único parámetro de capacidad de camión (TruckCap_Compra_General).
    """
    solver = pywraplp.Solver.CreateSolver('CBC')
    inf = solver.infinity()

    print("--- INICIANDO DEPURACIÓN CON MODELO DE CAMIÓN UNIFICADO ---")

    # --- Cargar datos reales para la prueba ---
    print("Cargando datos reales del escenario 'DemandaAlta'...")
    scenario_name = 'DemandaAlta'
    paths = {**config_paths.rutas_comunes, **config_paths.rutas_escenarios[scenario_name]}
    
    params_reales = {}
    params_reales.update(data_loader.cargar_parametros_generales(paths["Parametros Generales"]))
    s_especies, dens_s, area_s, trat_s = data_loader.cargar_datos_especies(paths['Datos Especies'])
    params_reales.update({'S_especies': s_especies, 'Dens_s': dens_s, 'Area_s': area_s, 'Trat_s': trat_s})
    g_poligonos, ha_g_total = data_loader.cargar_areas_poligonos(paths['Areas Poligonos'])
    params_reales.update({'G_poligonos': g_poligonos, 'Ha_g_total': ha_g_total})
    p_proveedores, disp_sp = data_loader.cargar_disponibilidad_y_proveedores(paths['Disponibilidad Especies'])
    c_sp = data_loader.cargar_costos_unitarios(paths['Costos Unitarios'], p_proveedores)
    params_reales.update({'P_proveedores': p_proveedores, 'Disponibilidad_{sp}': disp_sp, 'C_sp': c_sp})
    params_reales.setdefault('PC_U', params_reales.get('Costo_Unitario_Plantacion_PC', 1.0))
    print("Datos reales cargados.")

    # --- Crear un problema de juguete ---
    T = [1]
    G = [params_reales['G_poligonos'][0]] 
    S = [params_reales['S_especies'][0]]
    
    P_disponible = None
    for prov in params_reales['P_proveedores']:
        if params_reales['Disponibilidad_{sp}'].get((S[0], prov), 0) == 1:
            P_disponible = [prov]
            break
    if not P_disponible:
        print(f"ERROR: La especie '{S[0]}' no está disponible en ningún proveedor.")
        return
    P = P_disponible
    depot = '18'

    # --- Empezar con parámetros de juguete MUY GENEROSOS ---
    params_debug = {
        'Ha_g_total': {G[0]: 0.1},
        'Jornada_Laboral_JL_min': 99999,
        'PresupuestoTotal': 9999999,
        # CAMBIO: Ahora solo hay un parámetro de capacidad
        'TruckCap_Compra_General': 99999,
        # Copiamos los demás parámetros reales
        'Dens_s': params_reales['Dens_s'],
        'C_sp': params_reales['C_sp'],
        'PC_U': params_reales['PC_U'],
        'Trat_s': params_reales['Trat_s'],
        'Tiempo_Carga_LC_min': params_reales['Tiempo_Carga_LC_min'],
        'Tiempo_Descarga_LD_min': params_reales['Tiempo_Descarga_LD_min'],
    }

    # --- Sustituir los valores de juguete por los REALES, uno por uno ---
    print("\n--- Iniciando sustitución de parámetros ---")
    
    # 1. Demanda
    print(f"SUSTITUYENDO Ha_g_total. Valor real: {params_reales['Ha_g_total'][G[0]]}")
    params_debug['Ha_g_total'][G[0]] = params_reales['Ha_g_total'][G[0]]

    # 2. Tiempo
    #print(f"SUSTITUYENDO Jornada_Laboral_JL_min. Valor real: {params_reales['Jornada_Laboral_JL_min']}")
    #params_debug['Jornada_Laboral_JL_min'] = params_reales['Jornada_Laboral_JL_min']

    # 3. Presupuesto
    print(f"SUSTITUYENDO PresupuestoTotal. Valor real: {params_reales['Presupuesto_Total']}")
    params_debug['PresupuestoTotal'] = params_reales['Presupuesto_Total']

    # 4. Capacidad (ahora unificada)
    print(f"SUSTITUYENDO TruckCap_Compra_General. Valor real: {params_reales['TruckCap_Compra_General']}")
    params_debug['TruckCap_Compra_General'] = params_reales['TruckCap_Compra_General']


    # --- Construcción del Modelo con Lógica Unificada ---
    v = {}
    v['x'] = { (s, p, t): solver.IntVar(0, inf, f"x_{s}_{p}_{t}") for s in S for p in P for t in T }
    v['y'] = { (s, g, t): solver.IntVar(0, inf, f"y_{s}_{g}_{t}") for s in S for g in G for t in T }
    v['z1'] = { t: solver.IntVar(0, inf, f"z1_{t}") for t in T }
    v['z2'] = { (g, t): solver.IntVar(0, inf, f"z2_{g}_{t}") for g in G for t in T }
    v['d_B_plus'] = solver.NumVar(0, inf, "d_B_plus")
    v['d_B_minus'] = solver.NumVar(0, inf, "d_B_minus")

    # Requisito Principal
    for g in G:
        for s in S:
            solver.Add(sum(v['y'][s, g, t] / params_debug['Dens_s'][s] for t in T) >= params_debug['Ha_g_total'][g])
    # Conexión
    solver.Add(sum(v['y'].values()) <= sum(v['x'].values()))
    
    # Capacidad Vehículos (AMBAS RESTRICCIONES USAN EL MISMO PARÁMETRO)
    for t in T:
        solver.Add(sum(v['x'].values()) <= v['z1'][t] * params_debug['TruckCap_Compra_General'])
        for g in G:
            # ---> CAMBIO CLAVE AQUÍ <---
            solver.Add(sum(v['y'][s,g,t] for s in S) <= v['z2'][g, t] * params_debug['TruckCap_Compra_General'])

    # Jornada Laboral
    for t in T:
        solver.Add(sum(params_debug['Trat_s'][s] * v['y'][s, g, t] for s in S for g in G) + params_debug['Tiempo_Carga_LC_min'] * v['z1'][t] + sum(params_debug['Tiempo_Descarga_LD_min'] * v['z2'][g, t] for g in G) <= params_debug['Jornada_Laboral_JL_min'])
    # Meta Presupuesto
    costo_adquisicion = sum(v['x'][s, p, t] * params_debug['C_sp'][s, p] for s,p,t in v['x'].keys())
    costo_plantacion = sum(v['y'][s, g, t] * params_debug['PC_U'] for s,g,t in v['y'].keys())
    solver.Add(costo_adquisicion + costo_plantacion - v['d_B_plus'] + v['d_B_minus'] == params_debug['PresupuestoTotal'])
    
    solver.Minimize(costo_adquisicion + costo_plantacion)

    # --- Resolver y ver el resultado ---
    print("\nResolviendo el modelo unificado con los parámetros actuales...")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        print("\n>>>>> RESULTADO: El modelo es FACTIBLE y ÓPTIMO. <<<<<")
        print(f"      Costo Total Calculado = {solver.Objective().Value():.2f}")
    else:
        print("\n>>>>> !!!!! RESULTADO: El modelo es INFACTIBLE. !!!!! <<<<<")
        print("      La última sustitución que hiciste reveló el conflicto en tus datos.")

if __name__ == '__main__':
    encontrar_conflicto_unificado()