# model_fase1_ortools.py

from ortools.linear_solver import pywraplp

def solve_supply_model_gurobi(params):
    """
    TRADUCCIÓN FIEL: Orquesta la creación y resolución del modelo de Fase 1 con OR-Tools,
    implementando la lógica original de Programación por Metas.
    """
    solver = pywraplp.Solver.CreateSolver('CBC')
    if not solver:
        print("Error: No se pudo crear el solver CBC.")
        return None

    inf = solver.infinity()
    
    # --- 1. Extraer Conjuntos ---
    S = params['S_especies']
    P = params['P_proveedores']
    T = list(range(1, params['T_dias_planificacion'] + 1))
    G = params['G_poligonos']
    depot = '18'

    # --- 2. Declaración de Variables (Traducción 1 a 1) ---
    print("Fase 1 - OR-Tools (MILP Fiel): Declarando todas las variables...")
    v = {}
    # Variables principales
    v['x'] = { (s, p, t): solver.IntVar(0, inf, f"Compra_x_{s}_{p}_{t}") for s in S for p in P for t in T }
    v['y'] = { (s, g, t): solver.IntVar(0, inf, f"Plantacion_y_{s}_{g}_{t}") for s in S for g in G for t in T }
    # Nota: El inventario XI original tenía más dimensiones que no se usaban en las restricciones.
    # Se implementa la versión simplificada que sí se usa para que el modelo sea consistente.
    v['XI'] = { (s, t, 1, depot): solver.IntVar(0, inf, f"Inventario_XI_{s}_{t}_1_{depot}") for s in S for t in T }
    v['z1'] = { t: solver.IntVar(0, inf, f"VehiculosCompra_z1_{t}") for t in T }
    v['z2'] = { (g, t): solver.IntVar(0, inf, f"VehiculosDistrib_z2_{g}_{t}") for g in G for t in T }
    v['Desper'] = { (s, g, t): solver.IntVar(0, inf, f"Desperdicio_{s}_{g}_{t}") for s in S for g in G for t in T }
    
    # Variables de Desviación para Programación por Metas
    v['d_B_plus'] = solver.NumVar(0, inf, "Desv_Presupuesto_Pos")
    v['d_B_minus'] = solver.NumVar(0, inf, "Desv_Presupuesto_Neg")
    v['d_DesperTotal_plus'] = solver.NumVar(0, inf, "Desv_DesperdicioTotal_Pos")
    v['d_StockMin_minus'] = { s: solver.NumVar(0, inf, f"Desv_StockMin_Neg_{s}") for s in S }
    # Nota: Las demás variables de desviación (TiempoEntrega, Inventario, etc.) no estaban
    # implementadas en las restricciones de tu código original, por lo que se omiten aquí
    # para mantener la consistencia, pero se podrían añadir siguiendo este patrón.

    # --- 3. Definición de Restricciones (Traducción 1 a 1) ---
    print("Fase 1 - OR-Tools (MILP Fiel): Añadiendo restricciones del modelo original...")
    
    # Restricción de Balance de Inventario
    for s in S:
        for t in T:
            compras_llegando_hoy = sum(v['x'][s, p, t - 1] for p in P) if t > 1 else 0
            plantas_saliendo_hoy = sum(v['y'][s, g, t] for g in G)
            inventario_ayer = v['XI'][s, t - 1, 1, depot] if t > 1 else 0
            solver.Add(v['XI'][s, t, 1, depot] == inventario_ayer + compras_llegando_hoy - plantas_saliendo_hoy)


    # Capacidad de Vehículos de Distribución (usando la misma capacidad que la de compra)
    for t in T:
        for g in G:
            solver.Add(sum(v['y'][s, g, t] for s in S) <= v['z2'][g, t] * params['TruckCap_Compra_General'])


    # Restricción de Jornada Laboral
    for t in T:
        solver.Add(sum(params['Trat_s'][s] * v['y'][s, g, t] for s in S for g in G) +
                   params['Tiempo_Carga_LC_min'] * v['z1'][t] +
                   sum(params['Tiempo_Descarga_LD_min'] * v['z2'][g, t] for g in G) <= params['Jornada_Laboral_JL_min'])

    # Restricción de Cumplimiento de Reforestación por Área
    for g in G:
        solver.Add(sum(v['y'][s, g, t] / params['Dens_s'][s] for s in S for t in T) >= params['Ha_g_total'][g])

    # Restricción de Capacidad de Almacén
    for t in T:
        solver.Add(sum(v['XI'][s, t, 1, depot] * params['Area_s'][s] for s in S) <= params['Almacen_Capacidad_m2'])
    
    # --- Restricciones de Programación por Metas (Traducción 1 a 1) ---
    
    # Meta de Presupuesto
    costo_total_adquisicion = sum(v['x'][s, p, t] * params['C_sp'].get((s, p), 1e6) for s,p,t in v['x'].keys())
    costo_total_plantacion = sum(v['y'][s, g, t] * params['PC_U'] for s,g,t in v['y'].keys())
    presupuesto_total = params.get('PresupuestoTotal', params.get('Presupuesto_Total', 1e9)) # Compatibilidad
    solver.Add(costo_total_adquisicion + costo_total_plantacion - v['d_B_plus'] + v['d_B_minus'] == presupuesto_total)
    
    # Meta de Control de Desperdicio
    total_desperdiciado = sum(v['Desper'].values())
    total_comprado = sum(v['x'].values())
    max_desperdicio_pct = params.get('MaxDesperdicioPorcentaje', params.get('Max_Desperdicio_Porcentaje', 0.1)) # Compatibilidad
    solver.Add(total_desperdiciado <= max_desperdicio_pct * total_comprado)
    
    # Meta de Stock Mínimo
    T_max = params['T_dias_planificacion']
    stock_min_deseado = params.get('StockMinEspecie_s', params.get('Stock_Minimo_Deseado_Por_Especie', 10)) # Compatibilidad
    for s in S:
        inventario_final_s = v['XI'][s, T_max, 1, depot]
        solver.Add(inventario_final_s >= stock_min_deseado - v['d_StockMin_minus'][s])

    # --- 4. Función Objetivo de Programación por Metas (Traducción 1 a 1) ---
    print("Fase 1 - OR-Tools (MILP Fiel): Definiendo la función objetivo por metas...")
    pesos = {
        'w1': params.get('w_presupuesto', 1.0),
        'w6': params.get('w_penalidad_desperdicio', 5.0),
        'w7': params.get('w_desperdicio_total', 1.0), # Esta desviación no se definió en las restricciones
        'w8': params.get('w_stock_minimo', 10.0)
    }
    
    objetivo = solver.Sum([
        # Meta 1: Presupuesto
        pesos['w1'] * (v['d_B_plus'] + v['d_B_minus']),
        
        # Meta 6: Penalización directa por Desperdicio
        pesos['w6'] * sum(params.get('DesperPenalty_s', 1.0) * var for var in v['Desper'].values()),
        
        # Meta 8: Penalización por Faltante de Stock Mínimo
        pesos['w8'] * sum(v['d_StockMin_minus'].values())
    ])
    
    solver.Minimize(objetivo)
    
    # --- 5. Resolución y Extracción de Resultados ---
    print("Fase 1 - OR-Tools (MILP Fiel): Resolviendo el modelo...")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        print(f'Solución óptima encontrada en {solver.wall_time() / 1000:.2f} segundos.')
        print(f'Valor objetivo = {solver.Objective().Value():.2f}')
        
        results = {}
        for key, var_dict in v.items():
            if isinstance(var_dict, dict):
                results[key] = {idx: var.solution_value() for idx, var in var_dict.items() if var.solution_value() > 0.1}
            else: # Para variables únicas como d_B_plus
                if var_dict.solution_value() > 0.1:
                    results[key] = var_dict.solution_value()
        return results
    else:
        status_text = "No óptimo"
        if status == pywraplp.Solver.INFEASIBLE:
            status_text = "Infactible"
        print(f"El modelo de Fase 1 no encontró una solución óptima. Estado: {status_text}")
        return None