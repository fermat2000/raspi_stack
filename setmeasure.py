from influxdb import InfluxDBClient

client = InfluxDBClient(host='localhost', port=8087)
client.switch_database('metrics')

data = [{
    "measurement": "temperatura",
    "fields": {"valor": 23.5}
}]

client.write_points(data)
