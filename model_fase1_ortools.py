# model_fase1_ortools.py (Versión Completa, Robusta y Final)

from ortools.linear_solver import pywraplp

def solve_supply_model_gurobi(params, scenario_name):
    
    """
    Versión final y completa del modelo de Fase 1. Incluye todas las
    restricciones operativas y la solución al problema de estabilidad numérica.
    """
    solver = pywraplp.Solver.CreateSolver('CBC')
    if not solver:
        return None

    print("--- EJECUTANDO MODELO OPERACIONAL COMPLETO Y ROBUSTO ---")
    inf = solver.infinity()
    
    # --- 1. Extraer Conjuntos ---
    T = list(range(1, params['T_dias_planificacion'] + 1))
    S, P, G, depot = params['S_especies'], params['P_proveedores'], params['G_poligonos'], '18'

    # --- 2. Declaración de TODAS las Variables ---
    v = {}
    v['x'] = {(s, p, t): solver.IntVar(0, inf, f"x_{s}_{p}_{t}") for s in S for p in P for t in T}
    v['y'] = {(s, g, t): solver.IntVar(0, inf, f"y_{s}_{g}_{t}") for s in S for g in G for t in T}
    v['z1'] = {t: solver.IntVar(0, inf, f"z1_{t}") for t in T}
    v['z2'] = {(g, t): solver.IntVar(0, inf, f"z2_{g}_{t}") for g in G for t in T}
    v['XI'] = {(s, t): solver.IntVar(0, inf, f"XI_{s}_{t}") for s in S for t in T} # Inventario en depot

    # --- 3. TODAS las Restricciones Operativas (Duras) ---
    
    # Cumplimiento de Reforestación por Área
    for g in G:
        solver.Add(sum(v['y'][s, g, t] / params['Dens_s'][s] for s in S for t in T) >= params['Ha_g_total'][g] - 0.001)

    # Balance de Inventario
    for s in S:
        for t in T:
            compras_hoy = sum(v['x'][s, pr, t] for pr in P if params['Disponibilidad_{sp}'].get((s, pr), 0) == 1)
            plantas_hoy = sum(v['y'][s, g, t] for g in G)
            inv_ayer = v['XI'][s, t - 1] if t > 1 else 0
            solver.Add(v['XI'][s, t] == inv_ayer + compras_hoy - plantas_hoy)

    # Resto de restricciones operativas
    for t in T:
        # Capacidad de vehículos
        solver.Add(sum(v['x'][s, pr, t] for s in S for pr in P) <= v['z1'][t] * params['TruckCap_Compra_General'])
        for g in G:
            solver.Add(sum(v['y'][s, g, t] for s in S) <= v['z2'][g, t] * params['TruckCap_P1Distrib'])
        
        # Jornada Laboral
        solver.Add(sum(params['Trat_s'][s] * v['y'][s, g, t] for s in S for g in G) + params['Tiempo_Carga_LC_min'] * v['z1'][t] + sum(params['Tiempo_Descarga_LD_min'] * v['z2'][g, t] for g in G) <= params['Jornada_Laboral_JL_min'])
        
        # Capacidad de Almacén
        solver.Add(sum(v['XI'][s, t] * params['Area_s'][s] for s in S) <= params['Almacen_Capacidad_m2'])
        
        # Límite de Viajes Diarios
        solver.Add(v['z1'][t] <= params['Max_Viajes_Compra_Dia'])

    # --- 4. Función Objetivo: MINIMIZAR COSTO TOTAL (versión robusta) ---
    # La clave está en el 'if' para evitar los costos infinitos que causaban la inestabilidad.
    costo_total_adquisicion = sum(
        v['x'][s, p, t] * params['C_sp'].get((s, p), 0)
        for s in S for p in P for t in T
        if params['Disponibilidad_{sp}'].get((s, p), 0) == 1
    )
    costo_total_plantacion = sum(v['y'][s, g, t] * params['PC_U'] for s,g,t in v['y'].keys())
    solver.Minimize(costo_total_adquisicion + costo_total_plantacion)
    
    # --- 5. Resolver el Modelo Final y Completo ---
    print("\nResolviendo el modelo operacional completo...")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        print("\n" + "="*60)
        print("¡ÉXITO! SE ENCONTRÓ UN PLAN COMPLETO Y FACTIBLE.")
        print("="*60)
        costo = solver.Objective().Value()
        print(f"\nEl costo mínimo para ejecutar el plan de '{scenario_name}' es: ${costo:,.2f}")        
        
        results = {}
        for key, var_dict in v.items():
            if isinstance(var_dict, dict):
                results[key] = {idx: var.solution_value() for idx, var in var_dict.items() if var.solution_value() > 0.1}
        return results
    else:
        print("\nERROR INESPERADO: El modelo completo sigue siendo infactible.")
        return None