#!/usr/bin/env python3
"""Wake-on-LAN: envia magic packet via wlan0 (bypass da VPN)."""
import os
import socket

MAC = os.getenv('PC_MAC', '30:9c:23:a1:38:41')
BROADCAST = os.getenv('PC_BROADCAST', '192.168.0.255')
IFACE = os.getenv('PC_IFACE', 'wlan0')
SO_BINDTODEVICE = 25

parts = MAC.split(':')
addr = bytes(int(p, 16) for p in parts)
packet = b'\xff' * 6 + addr * 16

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
s.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, IFACE.encode())
s.sendto(packet, (BROADCAST, 9))
s.close()
print('WOL: Magic packet enviado para', MAC, 'via', IFACE)
