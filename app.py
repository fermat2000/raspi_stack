from flask import Flask, jsonify
from influxdb import InfluxDBClient
from datetime import datetime
import subprocess


app = Flask(__name__)

@app.route('/')
def home():
    fh = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    temp = subprocess.check_output(["vcgencmd", "measure_temp"]).decode()
    temp = temp.replace("temp=", "").strip()
    return f"Hola desde Flask Raspberry - Fecha y hora: {fh} - Temperatura: {temp}"    
##    return "¡Hola Fer desde Flask sin Docker!"

@app.route('/datos')
def mostrar_datos():
    client = InfluxDBClient(host='localhost', port=8086)
    client.switch_database('metrics')

    # Consulta: últimos 10 puntos de "temperatura"
    resultados = client.query('SELECT * FROM temperatura ORDER BY time DESC')
    puntos = list(resultados.get_points())

    return jsonify(puntos)  # Devuelve JSON

from flask import render_template

@app.route('/tabla')
def tabla():
    client = InfluxDBClient(host='localhost', port=8086)
    client.switch_database('metrics')
    resultados = client.query('SELECT * FROM temperatura ORDER BY time DESC')
    puntos = list(resultados.get_points())
    return render_template('tabla.html', datos=puntos)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
