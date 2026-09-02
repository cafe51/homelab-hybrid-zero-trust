import os
import socket

PC_IP = os.getenv('PC_IP', '192.168.0.11')
PC_PORT = int(os.getenv('PC_PORT', '9876'))
IFACE = os.getenv('PC_IFACE', 'wlan0')
SO_BINDTODEVICE = 25

def _request(method, path, timeout=5):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, IFACE.encode())
    s.settimeout(timeout)
    try:
        s.connect((PC_IP, PC_PORT))
        req = f'{method} {path} HTTP/1.0\r\nHost: pc\r\n\r\n'
        s.send(req.encode())
        resp = s.recv(4096).decode()
        s.close()
        body = resp.split('\r\n\r\n', 1)[-1].strip()
        return True, body
    except Exception as e:
        try:
            s.close()
        except:
            pass
        return False, str(e)

def get_status():
    ok, body = _request('GET', '/status')
    if ok and 'online' in body:
        return 'online'
    return 'offline'

def shutdown():
    return _request('POST', '/shutdown', timeout=2)

def hibernate():
    return _request('POST', '/hibernate', timeout=2)
