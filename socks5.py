#!/usr/bin/env python3
"""
SOCKS5 Residential Proxy Server with SO_BINDTODEVICE (Linux/Android Root)
--------------------------------------------------------------------------
Forwards outgoing connections through a physical network interface (e.g., wlan0)
bypassing active VPN routing tables (tun0) to present a clean residential IP
to target hosts (e.g., Cloudflare-protected indexers).
"""

import os
import sys
import socket
import select
import struct
import threading
import logging

PORT = int(os.getenv("SOCKS5_PORT", "1081"))
HOST = os.getenv("SOCKS5_HOST", "0.0.0.0")
IFACE = os.getenv("SOCKS5_IFACE", "wlan0")
SO_BINDTODEVICE = 25

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def handle_client(client_sock, client_addr):
    try:
        # 1. SOCKS5 Authentication negotiation
        auth_header = client_sock.recv(2)
        if len(auth_header) < 2:
            client_sock.close()
            return
        version, nmethods = struct.unpack("!BB", auth_header)
        methods = client_sock.recv(nmethods)
        
        # Respond: Version 5, No Authentication Required (0x00)
        client_sock.sendall(b"\x05\x00")

        # 2. SOCKS5 Request details
        req_header = client_sock.recv(4)
        if len(req_header) < 4:
            client_sock.close()
            return
            
        version, cmd, _, address_type = struct.unpack("!BBBB", req_header)
        if cmd != 1:  # 1 = CONNECT
            client_sock.close()
            return

        if address_type == 1:  # IPv4
            dest_addr = socket.inet_ntoa(client_sock.recv(4))
        elif address_type == 3:  # Domain name
            domain_len_raw = client_sock.recv(1)
            if not domain_len_raw:
                client_sock.close()
                return
            domain_len = ord(domain_len_raw)
            dest_addr = client_sock.recv(domain_len).decode("utf-8", errors="ignore")
        elif address_type == 4:  # IPv6
            dest_addr = socket.inet_ntop(socket.AF_INET6, client_sock.recv(16))
        else:
            client_sock.close()
            return

        dest_port = struct.unpack("!H", client_sock.recv(2))[0]

        # 3. Create outgoing socket bound to physical interface (wlan0)
        remote_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            remote_sock.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, IFACE.encode("utf-8"))
        except PermissionError:
            logging.warning("SO_BINDTODEVICE requires root privileges. Running without interface binding.")
        except Exception as e:
            logging.warning(f"Could not bind to interface {IFACE}: {e}")

        remote_sock.settimeout(15)
        try:
            remote_sock.connect((dest_addr, dest_port))
            # SOCKS5 Reply: Success (0x00)
            bind_addr, bind_port = remote_sock.getsockname()[:2]
            reply = b"\x05\x00\x00\x01" + socket.inet_aton(bind_addr) + struct.pack("!H", bind_port)
            client_sock.sendall(reply)
        except Exception as e:
            # SOCKS5 Reply: General Failure (0x01)
            client_sock.sendall(b"\x05\x01\x00\x01\x00\x00\x00\x00\x00\x00")
            client_sock.close()
            remote_sock.close()
            return

        remote_sock.settimeout(None)
        client_sock.settimeout(None)

        # 4. Bi-directional stream forwarding
        forward(client_sock, remote_sock)
    except Exception as e:
        pass
    finally:
        try:
            client_sock.close()
        except:
            pass

def forward(src, dst):
    sockets = [src, dst]
    while True:
        try:
            r, _, x = select.select(sockets, [], sockets, 60)
            if x or not r:
                break
            for s in r:
                data = s.recv(32768)
                if not data:
                    return
                target = dst if s is src else src
                target.sendall(data)
        except Exception:
            break

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(128)
    logging.info(f"SOCKS5 Residential Proxy listening on {HOST}:{PORT} (Outbound IFACE: {IFACE})")

    while True:
        try:
            client_sock, client_addr = server.accept()
            threading.Thread(target=handle_client, args=(client_sock, client_addr), daemon=True).start()
        except KeyboardInterrupt:
            break
        except Exception as e:
            logging.error(f"Error accepting connection: {e}")

if __name__ == "__main__":
    main()
