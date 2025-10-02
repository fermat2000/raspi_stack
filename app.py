from flask import Flask, jsonify, render_template, request
from influxdb import InfluxDBClient
from datetime import datetime
import subprocess
import math


app = Flask(__name__)

def contar_registros_influxdb(client, measurement='temperatura'):
    """
    Función helper para contar registros en InfluxDB de manera eficiente
    """
    try:
        # Método 1: Intentar con COUNT(*)
        count_query = f'SELECT COUNT(*) FROM {measurement}'
        result = client.query(count_query)
        points = list(result.get_points())
        
        if points:
            # Diferentes versiones de InfluxDB pueden usar diferentes nombres
            point = points[0]
            # Buscar la clave que contiene el conteo
            for key, value in point.items():
                if 'count' in key.lower() or key == 'value':
                    return int(value)
        
        # Método 2: Fallback - obtener una muestra y estimar
        sample_query = f'SELECT * FROM {measurement} ORDER BY time DESC LIMIT 1000'
        sample_result = client.query(sample_query)
        sample_count = len(list(sample_result.get_points()))
        
        if sample_count == 1000:
            # Si tenemos 1000 registros, probablemente hay más
            # Hacer un conteo menos eficiente pero más preciso
            all_query = f'SELECT time FROM {measurement}'
            all_result = client.query(all_query)
            return len(list(all_result.get_points()))
        else:
            return sample_count
            
    except Exception as e:
        print(f"Error al contar registros: {e}")
        return 0

@app.route('/')
def home():
    """
    Endpoint principal que muestra la fecha/hora actual y la temperatura de la Raspberry Pi
    """
    fh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    temp = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
    temp = temp.replace("temp=", "").strip()
    return f"Hola desde Flask Raspberry - Fecha y hora: {fh} - Temperatura: {temp}"    
##    return "¡Hola Fer desde Flask sin Docker!"

@app.route('/datos')
def mostrar_datos():
    """
    Retorna los últimos datos de temperatura almacenados en InfluxDB en formato JSON
    """
    client = InfluxDBClient(host='localhost', port=8086)
    client.switch_database('metrics')

    # Consulta: últimos 10 puntos de "temperatura"
    resultados = client.query('SELECT * FROM temperatura ORDER BY time DESC')
    puntos = list(resultados.get_points())

    return jsonify(puntos)  # Devuelve JSON

from flask import render_template

@app.route('/tabla')
def tabla():
    """
    Renderiza una tabla HTML con los datos de temperatura desde InfluxDB
    """
    client = InfluxDBClient(host='localhost', port=8086)
    client.switch_database('metrics')
    resultados = client.query('SELECT * FROM temperatura ORDER BY time DESC')
    puntos = list(resultados.get_points())
    return render_template('tabla.html', datos=puntos)

@app.route('/tabla-paginada')
def tabla_paginada():
    """
    Renderiza una tabla HTML con paginación de los datos de temperatura desde InfluxDB
    """
    # Parámetros de paginación desde la URL
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = request.args.get('por_pagina', 10, type=int)
    
    # Validar parámetros
    if pagina < 1:
        pagina = 1
    if por_pagina < 1 or por_pagina > 20:  # Límite máximo de 100 registros por página
        por_pagina = 10
    
    # Conectar a InfluxDB
    client = InfluxDBClient(host='localhost', port=8086)
    client.switch_database('metrics')
    
    # Obtener el total de registros usando la función helper
    total_registros = contar_registros_influxdb(client, 'temperatura')
    
    # Calcular offset para la paginación
    offset = (pagina - 1) * por_pagina
    
    # Consulta con LIMIT y OFFSET para paginación
    query_paginada = f'SELECT * FROM temperatura ORDER BY time DESC LIMIT {por_pagina} OFFSET {offset}'
    resultados = client.query(query_paginada)
    puntos = list(resultados.get_points())
    
    # Calcular información de paginación
    total_paginas = math.ceil(total_registros / por_pagina) if total_registros > 0 else 1
    
    # Información de paginación para el template
    paginacion = {
        'pagina_actual': pagina,
        'por_pagina': por_pagina,
        'total_registros': total_registros,
        'total_paginas': total_paginas,
        'tiene_anterior': pagina > 1,
        'tiene_siguiente': pagina < total_paginas,
        'pagina_anterior': pagina - 1 if pagina > 1 else None,
        'pagina_siguiente': pagina + 1 if pagina < total_paginas else None,
        'inicio_registro': offset + 1 if puntos else 0,
        'fin_registro': offset + len(puntos)
    }
    
    return render_template('tabla_paginada.html', datos=puntos, paginacion=paginacion)

@app.route('/api/datos-paginados')
def api_datos_paginados():
    """
    API que retorna datos de temperatura paginados en formato JSON
    """
    # Parámetros de paginación desde la URL
    pagina = request.args.get('pagina', 1, type=int)
    por_pagina = request.args.get('por_pagina', 10, type=int)
    
    # Validar parámetros
    if pagina < 1:
        pagina = 1
    if por_pagina < 1 or por_pagina > 100:
        por_pagina = 10
    
    # Conectar a InfluxDB
    client = InfluxDBClient(host='localhost', port=8086)
    client.switch_database('metrics')
    
    # Obtener el total de registros usando la función helper
    total_registros = contar_registros_influxdb(client, 'temperatura')
    
    # Calcular offset para la paginación
    offset = (pagina - 1) * por_pagina
    
    # Consulta con LIMIT y OFFSET para paginación
    query_paginada = f'SELECT * FROM temperatura ORDER BY time DESC LIMIT {por_pagina} OFFSET {offset}'
    resultados = client.query(query_paginada)
    puntos = list(resultados.get_points())
    
    # Calcular información de paginación
    total_paginas = math.ceil(total_registros / por_pagina) if total_registros > 0 else 1
    
    # Respuesta JSON con metadata de paginación
    return jsonify({
        'datos': puntos,
        'paginacion': {
            'pagina_actual': pagina,
            'por_pagina': por_pagina,
            'total_registros': total_registros,
            'total_paginas': total_paginas,
            'tiene_anterior': pagina > 1,
            'tiene_siguiente': pagina < total_paginas
        },
        'enlaces': {
            'primera': f'/api/datos-paginados?pagina=1&por_pagina={por_pagina}',
            'anterior': f'/api/datos-paginados?pagina={pagina-1}&por_pagina={por_pagina}' if pagina > 1 else None,
            'siguiente': f'/api/datos-paginados?pagina={pagina+1}&por_pagina={por_pagina}' if pagina < total_paginas else None,
            'ultima': f'/api/datos-paginados?pagina={total_paginas}&por_pagina={por_pagina}'
        }
    })

@app.route('/endpoints')
def listar_endpoints():
    """
    Endpoint que retorna información sobre todos los endpoints disponibles en la aplicación
    """
    endpoints = []
    
    for rule in app.url_map.iter_rules():
        endpoint_info = {
            'endpoint': rule.endpoint,
            'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),  # Excluir métodos HEAD y OPTIONS por defecto
            'url': rule.rule,
            'description': app.view_functions[rule.endpoint].__doc__ or 'Sin descripción disponible'
        }
        endpoints.append(endpoint_info)
    
    return jsonify({
        'total_endpoints': len(endpoints),
        'endpoints': endpoints
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
