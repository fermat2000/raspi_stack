import platform
import psutil

def get_info():
    return {
        "sistema": platform.system(),
        "arquitectura": platform.machine(),
        "cpu": psutil.cpu_percent(),
        "memoria": psutil.virtual_memory().percent,
        "usuario": psutil.users()[0].name if psutil.users() else "N/A"
    }