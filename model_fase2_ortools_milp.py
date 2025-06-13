# model_fase2_ortools_milp.py

from ortools.linear_solver import pywraplp

def solve_vrp_analytically(dia, demandas_diarias, matriz_tiempos, vehiculos, params):
    """
    TRADUCCIÓN FIEL: Resuelve el VRP para un día específico usando un modelo MILP exacto
    con OR-Tools (Solver CBC).
    """
    print(f"\n--- [Día {dia}] Iniciando VRP con Solver Analítico (OR-Tools MILP) ---")
    
    # --- 1. Preparación de Conjuntos y Parámetros ---
    depot = '18'
    nodos_con_demanda = list(demandas_diarias.keys())

    if not nodos_con_demanda:
        print(f"Día {dia}: No hay demanda, no se requiere ruteo.")
        return {'rutas': [], 'tiempo_total': 0, 'status': 'Sin Demanda'}

    N = [depot] + nodos_con_demanda
    K = [v['id'] for v in vehiculos]
    num_nodos_clientes = len(nodos_con_demanda)
    
    tiempo_servicio = params.get('Tiempo_Descarga_LD_min', 0)
    jornada_limite = params.get('Jornada_Laboral_JL_min', 480)

    # --- 2. Creación del Modelo OR-Tools ---
    # CBC (COIN-OR Branch and Cut) es un solver MILP analítico de código abierto.
    solver = pywraplp.Solver.CreateSolver('CBC')
    if not solver:
        print("Error: No se pudo crear el solver CBC.")
        return None

    # --- 3. Declaración de Variables de Decisión ---
    # x[i, j, k] = 1 si el vehículo k viaja del nodo i al j
    x = {(i, j, k): solver.BoolVar(f'x_{i}_{j}_{k}') for i in N for j in N for k in K if i != j}
    
    # u[i] para la eliminación de subtours (MTZ)
    u = {i: solver.IntVar(1, num_nodos_clientes, f'u_{i}') for i in nodos_con_demanda}

    # --- 4. Sistema de Restricciones (Traducción 1 a 1) ---
    
    # Cada nodo con demanda debe ser visitado exactamente una vez.
    for j in nodos_con_demanda:
        solver.Add(solver.Sum(x[i, j, k] for i in N if i != j for k in K) == 1, f'VisitaUnica_{j}')

    # Cada vehículo sale del depósito como máximo una vez.
    for k in K:
        solver.Add(solver.Sum(x[depot, j, k] for j in nodos_con_demanda) <= 1, f'SalidaDepot_{k}')

    # Conservación de flujo: si un vehículo entra a un nodo, debe salir.
    for h in nodos_con_demanda:
        for k in K:
            entradas = solver.Sum(x[i, h, k] for i in N if i != h)
            salidas = solver.Sum(x[h, j, k] for j in N if j != h)
            solver.Add(entradas == salidas, f'Flujo_{h}_{k}')

    # Restricción de capacidad de cada vehículo.
    for k in K:
        capacidad_vehiculo = next(v['capacidad'] for v in vehiculos if v['id'] == k)
        carga_transportada = solver.Sum(demandas_diarias[j] * x[i, j, k] for j in nodos_con_demanda for i in N if i != j)
        solver.Add(carga_transportada <= capacidad_vehiculo, f'Capacidad_{k}')

    # Restricción de duración máxima de ruta.
    for k in K:
        tiempo_viaje = solver.Sum(matriz_tiempos.get((i, j), 1e6) * x[i, j, k] for i in N for j in N if i != j)
        tiempo_servicio_total = solver.Sum(tiempo_servicio * x[i, j, k] for j in nodos_con_demanda for i in N if i != j)
        solver.Add(tiempo_viaje + tiempo_servicio_total <= jornada_limite, f'DuracionRuta_{k}')

    # Eliminación de Subtours (Formulación de Miller-Tucker-Zemlin)
    for i in nodos_con_demanda:
        for j in nodos_con_demanda:
            if i != j:
                solver.Add(u[i] - u[j] + num_nodos_clientes * solver.Sum(x[i, j, k] for k in K) <= num_nodos_clientes - 1, f'MTZ_{i}_{j}')

    # --- 5. Función Objetivo ---
    # Minimizar el tiempo total de viaje (incluyendo servicio).
    # La lógica es idéntica, solo cambia la sintaxis para construir la suma.
    tiempo_total_objetivo = solver.Sum(
        (matriz_tiempos.get((i,j), 1e6) + tiempo_servicio) * x[i,j,k] 
        for i in N for j in N if i !=j and j != depot for k in K
    )
    solver.Minimize(tiempo_total_objetivo)
    
    # --- 6. Resolver el Modelo ---
    print(f"Día {dia}: Resolviendo VRP analítico (MILP) para {len(nodos_con_demanda)} nodos...")
    # Opcional: Establecer un límite de tiempo en milisegundos.
    # solver.SetTimeLimit(60000) # 60 segundos
    status = solver.Solve()

    # --- 7. Extraer y Reconstruir las Rutas ---
    if status == pywraplp.Solver.OPTIMAL:
        print(f"Día {dia}: Solución óptima encontrada. Tiempo total: {solver.Objective().Value():.2f} min.")
        solucion = {'rutas': [], 'tiempo_total': solver.Objective().Value(), 'status': 'Óptimo'}
        
        for k in K:
            # Verificar si el vehículo k fue utilizado
            salida_depot = sum(x[depot, j, k].solution_value() for j in nodos_con_demanda)
            if salida_depot > 0.5:
                ruta_k = [depot]
                nodo_actual = depot
                while True:
                    # Encontrar el siguiente nodo en la ruta
                    siguiente_nodo = None
                    for j in N:
                        if nodo_actual != j and (nodo_actual, j, k) in x and x[nodo_actual, j, k].solution_value() > 0.5:
                            siguiente_nodo = j
                            break
                    
                    if siguiente_nodo is None: # No se encontró un arco de salida
                        break
                        
                    ruta_k.append(siguiente_nodo)
                    nodo_actual = siguiente_nodo
                    
                    if nodo_actual == depot: # Se ha completado el ciclo y regresado al depósito
                        break
                    # Medida de seguridad para evitar bucles infinitos en casos extraños
                    if len(ruta_k) > num_nodos_clientes + 2:
                        print(f"Advertencia: Bucle infinito detectado en la reconstrucción de la ruta para el vehículo {k}.")
                        break
                        
                solucion['rutas'].append({'vehiculo': k, 'ruta': ruta_k})
        return solucion
    else:
        status_text = "No se encontró solución óptima"
        if status == pywraplp.Solver.INFEASIBLE:
            status_text = "Infactible"
        print(f"Día {dia}: {status_text}. Estado OR-Tools: {status}")
        return None