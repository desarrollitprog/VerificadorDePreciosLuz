"""
Cliente de heartbeat para servidores secundarios (kioskos).
Se ejecuta en cada nodo y reporta al backend-dashboard cada 60 segundos.
Configuración vía variables de entorno (o .env en la raíz de backend-api).
"""
import os
import time
import socket
import shutil

import requests
from dotenv import load_dotenv
import logging

load_dotenv()

LOG_FILE = os.getenv("HEARTBEAT_LOG_FILE", "heartbeat_client.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)
# ================== CONFIGURACIÓN (backend-dashboard) ==================

# URL base del backend-dashboard (donde está el endpoint /api/heartbeat)
DASHBOARD_BASE_URL = os.getenv("DASHBOARD_URL", "http://192.168.1.105:8000").rstrip("/")
HEARTBEAT_ENDPOINT = f"{DASHBOARD_BASE_URL}/api/heartbeat"

# API Key: debe coincidir con HEARTBEAT_API_KEY del .env del backend-dashboard
API_KEY = os.getenv("HEARTBEAT_API_KEY", "")

# Ruta del disco a monitorear (carpeta de multimedia o disco del kiosko)
DISK_PATH = os.getenv("HEARTBEAT_DISK_PATH", "C:\\" if os.name == "nt" else "/")

# Intervalo entre heartbeats (segundos)
HEARTBEAT_INTERVAL_SECONDS = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "60"))


def get_server_name() -> str:
    """Obtiene el hostname de la máquina."""
    return socket.gethostname()


def get_ip_address() -> str:
    """Obtiene la IP real de la red local (no docker, no loopback)."""
    # Permitir forzar la IP por variable de entorno
    forced_ip = os.getenv("HEARTBEAT_SERVER_IP")
    if forced_ip:
        return forced_ip

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()

    # Filtrar IPs internas de Docker (172.16.0.0/12)
    if ip.startswith("172."):
        # Buscar otra IP LAN válida; si netifaces no está disponible, no romper el heartbeat.
        try:
            import netifaces
        except ImportError:
            logging.warning("netifaces no está instalado; se usará IP detectada por socket")
            return ip

        for iface in netifaces.interfaces():
            addrs = netifaces.ifaddresses(iface).get(netifaces.AF_INET, [])
            for addr in addrs:
                candidate = addr.get('addr')
                if candidate and not candidate.startswith("172.") and not candidate.startswith("127."):
                    return candidate
    return ip


def get_disk_usage(path: str) -> tuple[int, int]:
    """Usa shutil.disk_usage. Retorna (total_bytes, used_bytes)."""
    usage = shutil.disk_usage(path)
    return int(usage.total), int(usage.used)


def send_heartbeat() -> dict:
    nombre_servidor = get_server_name()
    ip = get_ip_address()
    almacenamiento_total, almacenamiento_usado = get_disk_usage(DISK_PATH)

    payload = {
        "nombre_servidor": nombre_servidor,
        "ip": ip,
        "almacenamiento_total": almacenamiento_total,
        "almacenamiento_usado": almacenamiento_usado,
    }

    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY,
    }

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                HEARTBEAT_ENDPOINT,
                json=payload,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            logging.info(f"Heartbeat enviado: {response.json()}")
            return response.json()
        except Exception as e:
            logging.error(f"Intento {attempt}: Fallo al enviar heartbeat: {e}")
            if attempt < max_retries:
                time.sleep(5)
            else:
                logging.error("Se agotaron los reintentos para enviar heartbeat.")
                raise


def main() -> None:
    if not API_KEY:
        logging.error("HEARTBEAT_API_KEY no configurada. Define DASHBOARD_URL y HEARTBEAT_API_KEY en .env")
        return

    logging.info(f"Iniciando heartbeat client hacia {HEARTBEAT_ENDPOINT}")
    logging.info(f"Servidor: {get_server_name()}  Disco: {DISK_PATH}")

    while True:
        try:
            data = send_heartbeat()
            # Ya se loguea en send_heartbeat
        except Exception as e:
            logging.error(f"Fallo al enviar heartbeat: {e}")
        finally:
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
