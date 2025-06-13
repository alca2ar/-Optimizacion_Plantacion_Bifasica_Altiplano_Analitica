import os
import numpy as np
from PIL import Image, ImageDraw

def create_daily_route_gif(day_num, daily_routes_data, node_coords, map_path, truck_icon_path, output_dir):
    """
    Genera un GIF animado de las rutas de VRP para un día específico.

    Args:
        day_num (int): El número del día que se está animando.
        daily_routes_data (list): Una lista de diccionarios, donde cada diccionario representa una ruta
                                  y debe contener la clave 'Ruta_Nodos_Str'.
        node_coords (dict): Diccionario con las coordenadas de cada nodo. Formato: {nodo_id: (x, y)}.
        map_path (str): Ruta a la imagen del mapa de fondo.
        truck_icon_path (str): Ruta al ícono del camión.
        output_dir (str): Directorio donde se guardará el GIF resultante.
    
    Returns:
        str: La ruta completa al archivo GIF generado, o None si ocurrió un error.
    """
    if not node_coords:
        print(f"Día {day_num}: No hay datos de coordenadas, no se puede crear la animación.")
        return None
    
    if not daily_routes_data:
        print(f"Día {day_num}: No se proporcionaron datos de rutas para animar.")
        return None

    try:
        # --- 1. Cargar y Preparar Activos de Imagen ---
        # Carga la imagen del mapa y el ícono, convirtiéndolos a RGBA para soportar transparencias.
        map_img_base = Image.open(map_path).convert("RGBA")
        truck_icon = Image.open(truck_icon_path).convert("RGBA")
        
        # Redimensiona el ícono del camión a un tamaño manejable (ej. 40x40 pixeles)
        truck_icon = truck_icon.resize((40, 40), Image.Resampling.LANCZOS)

        # Prepara el objeto para dibujar sobre la imagen
        draw = ImageDraw.Draw(map_img_base)
        
        # Define una paleta de colores para diferenciar las rutas de múltiples vehículos
        colors = ["#FF0000", "#0000FF", "#00FF00", "#FFA500", "#800080", "#00FFFF", "#FF00FF"]

        # --- 2. Dibujar Elementos Estáticos (Nodos y Líneas de Ruta) ---
        # Se dibuja sobre la imagen base del mapa para que aparezcan en todos los frames.
        for idx, route_info in enumerate(daily_routes_data):
            color = colors[idx % len(colors)]
            
            # Obtiene la ruta como texto y la divide en una lista de nodos
            route_nodes = route_info['Ruta_Nodos_Str'].split(' -> ')
            
            # Dibuja las líneas que conectan los nodos de la ruta
            for i in range(len(route_nodes) - 1):
                start_node_name = route_nodes[i]
                end_node_name = route_nodes[i+1]
                
                # Obtiene las coordenadas usando .get() para evitar errores si un nodo no existe
                start_pos = node_coords.get(start_node_name)
                end_pos = node_coords.get(end_node_name)
                
                if start_pos and end_pos:
                    draw.line([start_pos, end_pos], fill=color, width=4)
            
            # Dibuja círculos para marcar la ubicación de cada nodo en la ruta
            for node_name in route_nodes:
                if node_name in node_coords:
                    x, y = node_coords[node_name]
                    # Dibuja un círculo exterior (borde) y uno interior para mejor visibilidad
                    draw.ellipse((x-7, y-7, x+7, y+7), fill=color, outline="black")
                    draw.ellipse((x-5, y-5, x+5, y+5), fill="white")

        # --- 3. Generar los Frames de la Animación ---
        frames = []
        
        # Itera sobre cada ruta del día
        for idx, route_info in enumerate(daily_routes_data):
            route_nodes = route_info['Ruta_Nodos_Str'].split(' -> ')

            # Itera sobre cada segmento de la ruta (de un nodo al siguiente)
            for i in range(len(route_nodes) - 1):
                start_node_name = route_nodes[i]
                end_node_name = route_nodes[i+1]
                
                start_pos_np = np.array(node_coords.get(start_node_name))
                end_pos_np = np.array(node_coords.get(end_node_name))

                # Si falta alguna coordenada, salta este segmento
                if start_pos_np is None or end_pos_np is None:
                    continue

                # Define cuántos pasos intermedios (frames) tendrá el movimiento del camión
                num_frames_per_segment = 20
                
                # Usa numpy.linspace para calcular las posiciones intermedias suavemente
                for j in range(num_frames_per_segment + 1):
                    # Interpola la posición actual del camión
                    current_pos = start_pos_np + (end_pos_np - start_pos_np) * (j / num_frames_per_segment)
                    
                    # Crea una copia del mapa con las rutas ya dibujadas para este frame
                    frame = map_img_base.copy()
                    
                    # Pega el ícono del camión en la posición interpolada
                    # Se resta la mitad del tamaño del ícono para centrarlo
                    truck_x, truck_y = int(current_pos[0]), int(current_pos[1])
                    frame.paste(truck_icon, (truck_x - 20, truck_y - 20), truck_icon)
                    
                    # Añade el frame terminado a la lista
                    frames.append(frame)

        # --- 4. Guardar la Secuencia de Frames como un Archivo GIF ---
        if frames:
            # Asegurarse de que el directorio de salida exista
            os.makedirs(output_dir, exist_ok=True)
            gif_path = os.path.join(output_dir, f"dia_{day_num}.gif")
            
            # Guarda el primer frame y luego añade el resto
            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=50,      # Duración de cada frame en milisegundos (20 frames/seg)
                loop=0,           # 0 para que el GIF se repita indefinidamente
                optimize=True     # Optimiza la paleta de colores para reducir el tamaño del archivo
            )
            print(f"[AnimGen] Día {day_num}: Animación guardada exitosamente en: {gif_path}")
            return gif_path
        else:
            print(f"[AnimGen] Día {day_num}: No se generaron frames, no se creará el archivo GIF.")
            return None

    except FileNotFoundError as e:
        print(f"Error en AnimGen: No se encontró un archivo de imagen. Revisa las rutas. Detalles: {e}")
        return None
    except Exception as e:
        print(f"Error inesperado al crear la animación para el día {day_num}: {e}")
        import traceback
        traceback.print_exc()
        return None