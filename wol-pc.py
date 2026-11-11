#!/usr/bin/env python3
"""Wake-on-LAN: envia magic packet via wlan0 (bypass da VPN) com redundância de broadcast e portas."""
import os
import socket
import time

def load_env():
    candidate_paths = [
        os.path.join(os.path.dirname(__file__), ".env"),
        os.path.expanduser("~/.env")
    ]
    for env_path in candidate_paths:
        if os.path.exists(env_path):
            try:
                with open(env_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

load_env()

MAC = os.getenv('PC_MAC', '00:11:22:33:44:55')
PC_IP = os.getenv('PC_IP', '192.168.0.100')
BROADCAST = os.getenv('PC_BROADCAST', '192.168.0.255')
IFACE = os.getenv('PC_IFACE', 'wlan0')
SO_BINDTODEVICE = 25

parts = MAC.split(':')
addr = bytes(int(p, 16) for p in parts)
packet = b'\xff' * 6 + addr * 16

targets = [
    (BROADCAST, 9),
    (BROADCAST, 7),
    ('255.255.255.255', 9),
    ('255.255.255.255', 7),
    (PC_IP, 9),
    (PC_IP, 7),
]

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
try:
    s.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, IFACE.encode())
except Exception:
    pass

for ip, port in targets:
    for _ in range(3):
        try:
            s.sendto(packet, (ip, port))
        except Exception:
            pass
    time.sleep(0.02)

s.close()
print(f'WOL: Magic packet enviado para {MAC} via {IFACE} (broadcast + unicast, portas 7/9)')
