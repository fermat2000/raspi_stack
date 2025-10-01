from flask import Flask, jsonify
from influxdb import InfluxDBClient
from datetime import datetime
import subprocess


app = Flask(__name__)

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
