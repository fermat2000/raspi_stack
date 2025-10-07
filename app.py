from flask import Flask, jsonify, render_template, request
import os
from dotenv import load_dotenv
from influxdb import InfluxDBClient
from datetime import datetime
import subprocess
import math
import platform
import psutil


load_dotenv()
app = Flask(__name__)

def get_influxdb_client():
    host = os.environ.get('INFLUXDB_HOST', 'influxdb')
    port = int(os.environ.get('INFLUXDB_PORT', 8086))
    username = os.environ.get('INFLUXDB_USER')
    password = os.environ.get('INFLUXDB_USER_PASSWORD')
    database = os.environ.get('INFLUXDB_DATABASE', 'metrics')
    if username and password:
        client = InfluxDBClient(host=host, port=port, username=username, password=password)
    else:
        client = InfluxDBClient(host=host, port=port)
    client.switch_database(database)
    return client

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
    Endpoint principal que muestra la fecha/hora actual y la temperatura del sistema
    """
    fh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        # Intentar obtener temperatura usando psutil
        if hasattr(psutil, 'sensors_temperatures'):
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    if entries:
                        temp = f"{entries[0].current:.1f}°C"
                        break
                else:
                    temp = "N/A (sin sensores)"
            else:
                temp = "N/A (sin sensores)"
        else:
            temp = "N/A (psutil sin soporte)"
    except Exception as e:
        temp = f"N/A (error: {str(e)})"
    sistema = platform.system()
    arquitectura = platform.machine()
    return jsonify({
        "sistema": sistema,
        "arquitectura": arquitectura,
        "fecha_hora": fh,
        "temperatura": temp,
        "mensaje": "🐳 Flask en Docker"
    })

@app.route('/datos')
def mostrar_datos():
    """
    Retorna los últimos datos de temperatura almacenados en InfluxDB en formato JSON
    """
    client = get_influxdb_client()
    # Consulta: últimos 10 puntos de "temperatura"
    resultados = client.query('SELECT * FROM temperatura ORDER BY time DESC')
    puntos = list(resultados.get_points())
    return jsonify(puntos)  # Devuelve JSON

@app.route('/tabla')
def tabla():
    """
    Renderiza una tabla HTML con los datos de temperatura desde InfluxDB
    """
    client = get_influxdb_client()
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
    client = get_influxdb_client()
    
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
    client = get_influxdb_client()
    
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

@app.route('/endpoints-page')
def endpoints_page():
    """
    Página HTML que muestra todos los endpoints disponibles en la aplicación de forma visual
    """
    endpoints = []
    
    for rule in app.url_map.iter_rules():
        # Obtener información del endpoint
        endpoint_info = {
            'endpoint': rule.endpoint,
            'methods': list(rule.methods - {'HEAD', 'OPTIONS'}),
            'url': rule.rule,
            'description': app.view_functions[rule.endpoint].__doc__ or 'Sin descripción disponible'
        }
        
        # Agregar categoría basada en la URL
        if '/api/' in rule.rule:
            endpoint_info['category'] = 'API'
            endpoint_info['icon'] = '🔗'
        elif '/tabla' in rule.rule:
            endpoint_info['category'] = 'Visualización'
            endpoint_info['icon'] = '📊'
        elif rule.rule in ['/', '/sistema']:
            endpoint_info['category'] = 'Principal'
            endpoint_info['icon'] = '🏠'
        elif '/endpoints' in rule.rule:
            endpoint_info['category'] = 'Documentación'
            endpoint_info['icon'] = '📋'
        else:
            endpoint_info['category'] = 'Otros'
            endpoint_info['icon'] = '⚙️'
        
        # Determinar el tipo de respuesta
        if 'json' in endpoint_info['description'].lower() or '/api/' in rule.rule or rule.rule == '/datos':
            endpoint_info['response_type'] = 'JSON'
        elif 'html' in endpoint_info['description'].lower() or 'renderiza' in endpoint_info['description'].lower():
            endpoint_info['response_type'] = 'HTML'
        else:
            endpoint_info['response_type'] = 'TEXT'
        
        endpoints.append(endpoint_info)
    
    # Agrupar endpoints por categoría
    categorias = {}
    for endpoint in endpoints:
        cat = endpoint['category']
        if cat not in categorias:
            categorias[cat] = []
        categorias[cat].append(endpoint)
    
    return render_template('endpoints_page.html', categorias=categorias, total_endpoints=len(endpoints))

@app.route('/grafica')
def grafica():
    """
    Renderiza una página HTML con una gráfica de los datos de temperatura desde InfluxDB
    """
    client = get_influxdb_client()
    resultados = client.query('SELECT * FROM temperatura ORDER BY time DESC LIMIT 100')
    puntos = list(resultados.get_points())
    print(puntos)
    # Invertir para mostrar la gráfica en orden cronológico
    puntos = puntos[::-1]
    # Extraer listas de tiempo y temperatura
    tiempos = [p['time'] for p in puntos]
    valores = [p.get('value', None) for p in puntos]
    return render_template('grafica.html', tiempos=tiempos, valores=valores)

if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(host=host, port=port)
