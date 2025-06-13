# diagnostico_final.py

from ortools.linear_solver import pywraplp
import config_paths
import data_loader

def ejecutar_diagnostico():
    """
    Añade y prueba cada restricción del modelo secuencialmente para identificar
    el punto exacto de infactibilidad con los datos completos del escenario.
    """
    print("--- INICIANDO DIAGNÓSTICO FINAL AUTOMATIZADO ---")

    # --- 1. Cargar datos completos del escenario problemático ---
    scenario_name = 'DemandaAlta'
    print(f"Cargando datos del escenario: {scenario_name}")
    paths = {**config_paths.rutas_comunes, **config_paths.rutas_escenarios[scenario_name]}
    params = {}
    params.update(data_loader.cargar_parametros_generales(paths["Parametros Generales"]))
    s_especies, dens_s, area_s, trat_s = data_loader.cargar_datos_especies(paths['Datos Especies'])
    params.update({'S_especies': s_especies, 'Dens_s': dens_s, 'Area_s': area_s, 'Trat_s': trat_s})
    g_poligonos, ha_g_total = data_loader.cargar_areas_poligonos(paths['Areas Poligonos'])
    params.update({'G_poligonos': g_poligonos, 'Ha_g_total': ha_g_total})
    p_proveedores, disp_sp = data_loader.cargar_disponibilidad_y_proveedores(paths['Disponibilidad Especies'])
    c_sp = data_loader.cargar_costos_unitarios(paths['Costos Unitarios'], p_proveedores)
    params.update({'P_proveedores': p_proveedores, 'Disponibilidad_{sp}': disp_sp, 'C_sp': c_sp})
    params.setdefault('PC_U', params.get('Costo_Unitario_Plantacion_PC', 1.0))
    print("Datos cargados.")

    # Aumentar artificialmente los recursos para aislar el conflicto estructural
    params['Jornada_Laboral_JL_min'] = 999999
    params['Presupuesto_Total'] = 99999999
    params['T_dias_planificacion'] = 200 # Un valor alto pero razonable

    # --- 2. Crear el modelo base con variables y objetivo simple ---
    solver = pywraplp.Solver.CreateSolver('CBC')
    inf = solver.infinity()
    T = list(range(1, params['T_dias_planificacion'] + 1))
    S, P, G, depot = params['S_especies'], params['P_proveedores'], params['G_poligonos'], '18'
    
    v = {}
    v['x'] = { (s, p, t): solver.IntVar(0, inf, f"x_{s}_{p}_{t}") for s in S for p in P for t in T }
    v['y'] = { (s, g, t): solver.IntVar(0, inf, f"y_{s}_{g}_{t}") for s in S for g in G for t in T }
    v['z1'] = { t: solver.IntVar(0, inf, f"z1_{t}") for t in T }
    v['z2'] = { (g, t): solver.IntVar(0, inf, f"z2_{g}_{t}") for g in G for t in T }
    v['XI'] = { (s, t): solver.IntVar(0, inf, f"XI_{s}_{t}") for s in S for t in T } # Inventario en depot
    solver.Minimize(sum(v['x'].values())) # Objetivo simple para que el solver funcione

    # --- 3. Definir cada restricción como una función separada ---
    
    def r_cumplimiento_area(solver, v, p):
        for g in p['G_poligonos']:
            solver.Add(sum(v['y'][s, g, t] / p['Dens_s'][s] for s in p['S_especies'] for t in T) >= p['Ha_g_total'][g] - 0.001)
        return "Cumplimiento de Reforestación por Área"

    def r_balance_inventario(solver, v, p):
        for s in p['S_especies']:
            for t in T:
                compras_llegando_hoy = sum(v['x'][s, pr, t] for pr in p['P_proveedores'])
                plantas_saliendo_hoy = sum(v['y'][s, g, t] for g in p['G_poligonos'])
                inv_ayer = v['XI'][s, t-1] if t > 1 else 0
                solver.Add(v['XI'][s, t] == inv_ayer + compras_llegando_hoy - plantas_saliendo_hoy)
        return "Balance de Inventario"

    def r_capacidad_vehiculos(solver, v, p):
        for t in T:
            solver.Add(sum(v['x'][s, pr, t] for s in p['S_especies'] for pr in p['P_proveedores']) <= v['z1'][t] * p['TruckCap_Compra_General'])
            for g in p['G_poligonos']:
                solver.Add(sum(v['y'][s, g, t] for s in p['S_especies']) <= v['z2'][g, t] * p['TruckCap_P1Distrib'])
        return "Capacidad de Vehículos"

    def r_jornada_laboral(solver, v, p):
        for t in T:
            solver.Add(sum(p['Trat_s'][s] * v['y'][s, g, t] for s in p['S_especies'] for g in p['G_poligonos']) + p['Tiempo_Carga_LC_min'] * v['z1'][t] + sum(p['Tiempo_Descarga_LD_min'] * v['z2'][g, t] for g in p['G_poligonos']) <= p['Jornada_Laboral_JL_min'])
        return "Jornada Laboral"

    def r_capacidad_almacen(solver, v, p):
        for t in T:
            solver.Add(sum(v['XI'][s, t] * p['Area_s'][s] for s in p['S_especies']) <= p['Almacen_Capacidad_m2'])
        return "Capacidad de Almacén"

    def r_limite_viajes_diarios(solver, v, p):
        for t in T:
            solver.Add(v['z1'][t] <= p['Max_Viajes_Compra_Dia'])
        return "Límite de Viajes Diarios de Adquisición"

    def r_disponibilidad_proveedor(solver, v, p):
        for s in p['S_especies']:
            for pr in p['P_proveedores']:
                if p['Disponibilidad_{sp}'].get((s, pr), 0) == 0:
                    for t in T:
                        solver.Add(v['x'][s, pr, t] == 0)
        return "Disponibilidad de Proveedor"
        
    # --- 4. Probar las restricciones en orden hasta que una falle ---
    restricciones_a_probar = [
        r_cumplimiento_area,
        r_disponibilidad_proveedor,
        r_balance_inventario,
        r_capacidad_vehiculos,
        r_limite_viajes_diarios,
        r_jornada_laboral,
        r_capacidad_almacen,
    ]

    print("\n--- Iniciando prueba secuencial de restricciones ---")
    for agregar_restriccion in restricciones_a_probar:
        nombre_restriccion = agregar_restriccion(solver, v, params)
        print(f"Probando con restricción: '{nombre_restriccion}'...")
        
        status = solver.Solve()
        
        if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
            print("  -> ESTADO: Factible. Continuando...")
        else:
            print("\n" + "#"*60)
            print(">>> ¡CONFLICTO ENCONTRADO! <<<")
            print(f"El modelo se vuelve INFACTIBLE al añadir la restricción:")
            print(f"          '{nombre_restriccion}'")
            print("#"*60)
            print("\nAnálisis: Esta regla, en combinación con las anteriores, crea una contradicción imposible de resolver con tus datos.")
            return

    print("\n--- DIAGNÓSTICO COMPLETADO ---")
    print("Si has llegado hasta aquí, todas las restricciones son compatibles individualmente.")
    print("El conflicto podría estar en la interacción de las metas (presupuesto, stock final).")


if __name__ == '__main__':
    ejecutar_diagnostico()