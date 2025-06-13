# data_loader.py

import pandas as pd

# --- Funciones para Cargar Datos desde CSV ---

def cargar_parametros_generales(filepath):
    """Carga los parámetros de configuración general desde un archivo CSV."""
    df = pd.read_csv(filepath)
    params = pd.Series(df.Valor.values, index=df.Parametro).to_dict()
    # Convertir a tipos correctos
    for key in ['T_dias_planificacion', 'TruckCap_Compra_General', 'Costo_Fijo_Camion_FC',
                'Costo_Unitario_Plantacion_PC', 'Tiempo_Carga_LC_min', 'Tiempo_Descarga_LD_min',
                'Jornada_Laboral_JL_min', 'Almacen_Capacidad_m2', 'Max_Viajes_Compra_Dia',
                'Max_Viajes_Distribucion_Dia', 'Stock_Minimo_Deseado_Por_Especie']:
        if key in params:
            try:
                # Se convierte a float primero para manejar casos como '1000.0'
                params[key] = int(float(params[key]))
            except (ValueError, TypeError):
                print(f"Advertencia en '{filepath}': No se pudo convertir el parámetro '{key}' ({params[key]}) a entero.")
    if 'Max_Desperdicio_Porcentaje' in params:
        try:
            params['Max_Desperdicio_Porcentaje'] = float(params['Max_Desperdicio_Porcentaje'])
        except (ValueError, TypeError):
            print(f"Advertencia en '{filepath}': No se pudo convertir 'Max_Desperdicio_Porcentaje' ({params['Max_Desperdicio_Porcentaje']}) a float.")
    if 'Presupuesto_Total' in params:
        try:
            params['Presupuesto_Total'] = float(params['Presupuesto_Total'])
        except (ValueError, TypeError):
            print(f"Advertencia en '{filepath}': No se pudo convertir 'Presupuesto_Total' ({params['Presupuesto_Total']}) a float.")
    return params

def cargar_datos_especies(filepath):
    """Carga los datos específicos de cada especie."""
    df = pd.read_csv(filepath)
    S_especies_list = df['Especie'].tolist()
    Dens_s_dict = pd.Series(df.Densidad_plantas_ha.values, index=df.Especie).to_dict()
    Area_s_dict = pd.Series(df.Area_por_planta_m2.values, index=df.Especie).to_dict()
    Trat_s_dict = pd.Series(df.Tiempo_Tratamiento_min.values, index=df.Especie).to_dict()
    return S_especies_list, Dens_s_dict, Area_s_dict, Trat_s_dict

def cargar_disponibilidad_y_proveedores(filepath):
    """Carga la disponibilidad de especies por proveedor."""
    df = pd.read_csv(filepath)
    P_proveedores_list = df.columns[1:].tolist()
    FactE_sp_dict = {}
    for index, row in df.iterrows():
        especie = row['Especie']
        for proveedor in P_proveedores_list:
            FactE_sp_dict[(especie, proveedor)] = int(row[proveedor])
    return P_proveedores_list, FactE_sp_dict

def cargar_costos_unitarios(filepath, proveedores_list=None):
    """Carga los costos unitarios por especie y proveedor, manejando valores no disponibles."""
    df = pd.read_csv(filepath)
    C_sp_dict = {}
    if proveedores_list is None:
        proveedores_list_actual = df.columns[1:].tolist()
    else:
        proveedores_list_actual = proveedores_list

    for index, row in df.iterrows():
        especie = row['Especie']
        for proveedor in proveedores_list_actual:
            if proveedor in df.columns:
                costo = row[proveedor]
                if pd.isna(costo) or str(costo).strip() in ['', '--', 'nan', 'NaN', '9999', '9999.0']:
                    C_sp_dict[(especie, proveedor)] = float('inf')
                else:
                    try:
                        C_sp_dict[(especie, proveedor)] = float(costo)
                    except ValueError:
                        C_sp_dict[(especie, proveedor)] = float('inf')
            else:
                C_sp_dict[(especie, proveedor)] = float('inf')
    return C_sp_dict

def cargar_areas_poligonos(filepath):
    """Carga las áreas de los polígonos a reforestar."""
    df = pd.read_csv(filepath)
    df['Poligono'] = df['Poligono'].astype(str)
    G_poligonos_list = df['Poligono'].tolist()
    Ha_g_total_dict = pd.Series(df.Area_ha.values, index=df.Poligono).to_dict()
    return G_poligonos_list, Ha_g_total_dict

def cargar_datos_vehiculos_vrp(filepath):
    """Carga los datos de los vehículos para el VRP."""
    df = pd.read_csv(filepath)
    K_vehiculos_nombres_list = df['Vehiculo_ID'].tolist()
    cap_k_vehiculos_vrp_list = df['Capacidad_Plantas'].tolist()
    return K_vehiculos_nombres_list, cap_k_vehiculos_vrp_list

def cargar_coordenadas_nodos(filepath):
    """Carga las coordenadas X, Y de los nodos desde un archivo CSV."""
    try:
        df = pd.read_csv(filepath)
        df['Nodo'] = df['Nodo'].astype(str)
        coords_dict = pd.Series(list(zip(df.x, df.y)), index=df.Nodo).to_dict()
        return coords_dict
    except FileNotFoundError:
        print(f"ADVERTENCIA: Archivo de coordenadas no encontrado en {filepath}.")
        return None
    except Exception as e:
        print(f"ERROR al cargar coordenadas de nodos: {e}")
        return None

def cargar_matriz_tiempos_vrp(filepath, depot_node_name='18', nodes_to_include=None):
    """Carga y procesa la matriz de tiempos/distancias para el VRP."""
    df = pd.read_csv(filepath, index_col=0)
    df.index = df.index.astype(str)
    df.columns = df.columns.astype(str)

    if depot_node_name not in df.index:
        raise ValueError(f"El nodo depot '{depot_node_name}' no se encuentra en la matriz de distancia.")
    
    if nodes_to_include:
        # Asegurarse de que el depot esté en la lista si se filtra
        if depot_node_name not in nodes_to_include:
            nodes_to_include.insert(0, depot_node_name)
        
        ordered_node_names_for_vrp = sorted(nodes_to_include, key=lambda x: (x != depot_node_name, int(x)))
        df_ordered = df.reindex(index=ordered_node_names_for_vrp, columns=ordered_node_names_for_vrp)
    else:
        # Comportamiento original si no se filtra: usar todos y poner el depot primero
        all_nodes = sorted(df.index.tolist(), key=lambda x: (x != depot_node_name, int(x)))
        df_ordered = df.reindex(index=all_nodes, columns=all_nodes)
        ordered_node_names_for_vrp = all_nodes

    df_ordered.fillna(99999, inplace=True) # Rellenar valores faltantes con un número alto
    
    return df_ordered.values.tolist(), ordered_node_names_for_vrp