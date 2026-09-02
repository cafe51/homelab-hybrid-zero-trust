#!/usr/bin/env python3
"""Mini servidor HTTP para shutdown/status do PC."""
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 9876

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"online"}')
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/shutdown':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"action":"shutdown"}')
            subprocess.Popen(['systemctl', 'poweroff', '-i'],
                             stdout=open('/home/japhe/pc-remote.log','a'), stderr=open('/home/japhe/pc-remote.log','a'))
        elif self.path == '/hibernate':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"action":"hibernate"}')
            subprocess.Popen(['systemctl', 'hibernate', '-i'],
                             stdout=open('/home/japhe/pc-remote.log','a'), stderr=open('/home/japhe/pc-remote.log','a'))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass

if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), Handler)
    while True:
        server.handle_request()
