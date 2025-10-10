import time
from datetime import datetime
from influxdb import InfluxDBClient
import uuid

#def leer_temperatura():
#    # Simulación: reemplazá con lectura real si tenés sensor
#    return 22.5

def leer_temperatura():
    with open("/sys/class/thermal/thermal_zone0/temp") as f:
        temp_millic = int(f.read())
    return temp_millic / 1000.0

def escribir_en_influx(valor):
    client = InfluxDBClient(host='localhost', port=8086)
    client.switch_database('metrics')

#    punto = [{
#        "measurement": "temperatura",
#        "time": datetime.utcnow().isoformat(),
#        "fields": {"valor": valor}
#    }]

    punto = [{
	   "measurement": "temperatura",
	    "time": datetime.utcnow().isoformat(),
	    "fields": {
	        "valor": valor,
	        "inserted_at": datetime.utcnow().isoformat(),
	        "uuid": str(uuid.uuid4())
	    },
	    "tags": {
	        "sensor": "raspi1"
	    }
    }]

    client.write_points(punto)
    print(f"[{datetime.now()}] Temperatura enviada: {valor}°C")

if __name__ == "__main__":
    while True:
        temp = leer_temperatura()
        escribir_en_influx(temp)
        time.sleep(300)  # 5 minutos
