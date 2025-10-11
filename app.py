from flask import Flask, jsonify, render_template, request
import os
from dotenv import load_dotenv
from influxdb import InfluxDBClient
from datetime import datetime
import subprocess
import math
import platform
import psutil
from sistema_info import get_info

load_dotenv()
app = Flask(__name__)

def get_influxdb_client():
    host = os.environ.get('INFLUXDB_HOST', 'localhost')
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

### ----------------------------------------------- ###
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
    
    # Formatear las fechas para mostrar en la tabla
    for punto in puntos:
        # Convierte el string ISO a datetime y lo formatea
        try:
            dt = datetime.strptime(punto['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            punto['time_fmt'] = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            punto['time_fmt'] = punto['time']  # fallback si falla el parseo
    
    return render_template('tabla_paginada.html', datos=puntos, paginacion=paginacion)

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

@app.route('/tabla-sistema-info')
def tabla_sistema_info():
    """
    Renderiza una tabla HTML con paginación y filtros de los datos de sistema_info desde InfluxDB
    """
    client = get_influxdb_client()
    # Parámetros de paginación y filtro
    pagina = int(request.args.get('pagina', 1))
    por_pagina = int(request.args.get('por_pagina', 10))
    host = request.args.get('host')
    sistema = request.args.get('sistema')

    # Construir la consulta con filtros
    where = []
    if host:
        where.append(f"host='{host}'")
    if sistema:
        where.append(f"sistema='{sistema}'")
    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    query = f"SELECT * FROM sistema_info {where_clause} ORDER BY time DESC LIMIT {por_pagina} OFFSET {(pagina-1)*por_pagina}"
    resultados = client.query(query)
    puntos = list(resultados.get_points())

    # Formatear la fecha
    for punto in puntos:
        try:
            dt = datetime.strptime(punto['time'], "%Y-%m-%dT%H:%M:%S.%fZ")
            punto['time_fmt'] = dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            punto['time_fmt'] = punto['time']

    # Obtener hosts y sistemas únicos para los filtros
    hosts = set()
    sistemas = set()
    all_results = client.query("SELECT host, sistema FROM sistema_info")
    for p in all_results.get_points():
        hosts.add(p.get('host'))
        sistemas.add(p.get('sistema'))

    # Para paginación: contar total de registros
    count_query = f"SELECT COUNT(*) FROM sistema_info {where_clause}"
    count_result = client.query(count_query)
    total = 0
    for point in list(count_result.get_points()):
        for key, value in point.items():
            if 'count' in key.lower() or key == 'value':
                total = int(value)
                break

    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

    return render_template(
        'tabla_sistema_info.html',
        datos=puntos,
        pagina=pagina,
        por_pagina=por_pagina,
        total_paginas=total_paginas,
        total=total,
        hosts=sorted(hosts),
        sistemas=sorted(sistemas),
        host_seleccionado=host,
        sistema_seleccionado=sistema
    )

@app.route('/servicios-activos-tabla')
def servicios_activos_tabla():
    """
    Muestra la lista de servicios activos en una tabla HTML usando systemctl
    """
    try:
        resultado = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager", "--no-legend"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True
        )
        servicios = []
        for linea in resultado.stdout.strip().split('\n'):
            if linea:
                partes = linea.split()
                nombre = partes[0]
                estado = partes[-2] if len(partes) > 2 else ""
                descripcion = " ".join(partes[1:-3]) if len(partes) > 4 else ""
                servicios.append({
                    "nombre": nombre,
                    "estado": estado,
                    "descripcion": descripcion
                })
        return render_template('servicios_activos.html', servicios=servicios)
    except Exception as e:
        return render_template('servicios_activos.html', servicios=[], error=str(e))

@app.route('/indice')
def indice():
    """
    Página índice con acceso a todos los endpoints disponibles
    """
    endpoints = []
    for rule in app.url_map.iter_rules():
        # Excluir endpoints internos de Flask
        if rule.endpoint != 'static':
            endpoints.append({
                'url': rule.rule,
                'methods': ', '.join(rule.methods - {'HEAD', 'OPTIONS'}),
                'description': app.view_functions[rule.endpoint].__doc__ or 'Sin descripción'
            })
    return render_template('indice.html', endpoints=endpoints)

@app.route('/grafica')
def grafica():
    """
    Renderiza una página HTML con una gráfica de los datos de temperatura desde InfluxDB
    """
    client = get_influxdb_client()
    resultados = client.query('SELECT * FROM temperatura ORDER BY time DESC LIMIT 100')
    puntos = list(resultados.get_points())
    
    # Invertir para mostrar la gráfica en orden cronológico
    puntos = puntos[::-1]
    # Extraer listas de tiempo y temperatura
    tiempos = [p['time'] for p in puntos]
    valores = [p.get('valor', None) for p in puntos]
    return render_template('grafica.html', tiempos=tiempos, valores=valores)

@app.route('/json-endpoints')
def json_endpoints():
    """
    Página HTML que muestra todos los endpoints que retornan JSON y permite ver su salida en vivo
    """
    # Filtrar endpoints que retornan JSON
    endpoints = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint != 'static':
            doc = app.view_functions[rule.endpoint].__doc__ or ''
            # Heurística: si la descripción menciona JSON o el endpoint es /api/ o /datos
            if 'json' in doc.lower() or '/api/' in rule.rule or rule.rule in ['/datos', '/sistema', '/sistema-info', '/status', '/endpoints']:
                endpoints.append({
                    'url': rule.rule,
                    'description': doc.strip() or 'Sin descripción'
                })
    return render_template('json_endpoints.html', endpoints=endpoints)

### ----------------------------------------------- ###
# jsonify
@app.route('/status')
def status():
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
# jsonify
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
# jsonify
@app.route('/sistema')
def sistema():
    """
    Retorna información del sistema en formato JSON
    """
    info = get_info()
    return jsonify(info)
# jsonify
@app.route('/sistema-info')
def sistema_info():
    """
    Consulta los últimos datos insertados en la medición sistema_info de InfluxDB.
    """
    client = get_influxdb_client()
    query = 'SELECT * FROM sistema_info ORDER BY time DESC LIMIT 1'
    result = client.query(query)
    points = list(result.get_points())
    if points:
        return jsonify(points[0])
    else:
        return jsonify({"error": "No hay datos en sistema_info"}), 404
# jsonify
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
# jsonify
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

### ----------------------------------------------- ###
if __name__ == '__main__':
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))
    app.run(host=host, port=port)
