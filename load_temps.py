import os
from influxdb import InfluxDBClient
from dotenv import load_dotenv
import time
import random

def load_temps(n_iteraciones=10, delay=1):
    """
    Inserta valores simulados en la tabla 'temperatura' de InfluxDB.
    n_iteraciones: cantidad de registros a insertar
    delay: segundos entre cada inserción
    """
    load_dotenv()
    host = os.environ.get('INFLUXDB_HOST', 'localhost')
    port = int(os.environ.get('INFLUXDB_PORT', 8087))
    username = os.environ.get('INFLUXDB_USER')
    password = os.environ.get('INFLUXDB_USER_PASSWORD')
    database = os.environ.get('INFLUXDB_DATABASE', 'metrics')

    if username and password:
        client = InfluxDBClient(host=host, port=port, username=username, password=password)
    else:
        client = InfluxDBClient(host=host, port=port)
    client.switch_database(database)

    for i in range(n_iteraciones):
        temp = round(random.uniform(20.0, 40.0), 2)
        punto = [{
            "measurement": "temperatura",
            "fields": {"valor": temp}
        }]
        client.write_points(punto)
        print(f"Registro {i+1}: {temp}°C insertado.")
        time.sleep(delay)

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    load_temps(n, 0.5)
