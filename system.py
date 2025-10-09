import platform
import psutil
import json
from datetime import datetime
from influxdb import InfluxDBClient
import os
from dotenv import load_dotenv

load_dotenv()  # Carga las variables del archivo .env

sistema = platform.system()
maquina = platform.machine()
print("sistema:",sistema)
print("maquina:",maquina)

def obtener_info_sistema():
    info = {
        "timestamp": datetime.now().isoformat(),
        "cpu": {
            "uso_porcentual": psutil.cpu_percent(interval=1),
            "nucleos_logicos": psutil.cpu_count(logical=True),
            "nucleos_fisicos": psutil.cpu_count(logical=False)
        },
        "ram": psutil.virtual_memory()._asdict(),
	    "disco": psutil.disk_usage('/')._asdict(),
	    "red": psutil.net_io_counters()._asdict(),
        "procesos": []
    }
    procesos = []
    for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
        try:
            
            procesos.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    top5 = sorted(procesos, key=lambda p: p['cpu_percent'], reverse=True)[:5]
    info["procesos"] =top5
    return info

def insertar_en_influx(info):
    host = os.environ.get('INFLUXDB_HOST', 'localhost')
    port = int(os.environ.get('INFLUXDB_PORT', 8087))
    db = os.environ.get('INFLUXDB_DATABASE', 'metrics')
    client = InfluxDBClient(host=host, port=port)
    client.switch_database(db)
    punto = {
        "measurement": "sistema_info",
        "tags": {
            "host": platform.node(),
            "sistema": platform.system(),
            "arquitectura": platform.machine()
        },
        "time": info["timestamp"],
        "fields": {
            "cpu_uso_porcentual": float(info["cpu"]["uso_porcentual"]),
            "cpu_nucleos_logicos": int(info["cpu"]["nucleos_logicos"]),
            "cpu_nucleos_fisicos": int(info["cpu"]["nucleos_fisicos"]),
            "ram_total": int(info["ram"]["total"]),
            "ram_disponible": int(info["ram"]["available"]),
            "ram_uso_porcentual": float(info["ram"]["percent"]),
            "disco_total": int(info["disco"]["total"]),
            "disco_usado": int(info["disco"]["used"]),
            "disco_libre": int(info["disco"]["free"]),
            "disco_uso_porcentual": float(info["disco"]["percent"]),
            "red_bytes_enviados": int(info["red"]["bytes_sent"]),
            "red_bytes_recibidos": int(info["red"]["bytes_recv"])
        }
    }
    client.write_points([punto])

if __name__ == "__main__":
    while True:
        datos = obtener_info_sistema()
        insertar_en_influx(datos)
        time.sleep(900)  # 5 minutos

