import os
import subprocess
import json
import socket
import urllib.request
import urllib.error
from flask import Flask, jsonify, render_template

# Adiciona home ao path para importar pc_client
import sys
sys.path.insert(0, '/data/data/com.termux/files/home')

app = Flask(__name__)

# Config
RCLONE_URL = "http://localhost:5575/core/stats"
TRANSMISSION_RPC_URL = "http://localhost:9091/transmission/rpc"

def get_disk_space():
    try:
        output = subprocess.check_output(['df', '-k', '/data']).decode('utf-8')
        lines = output.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            avail_kb = int(parts[3])
            return {"avail_gib": round(avail_kb / 1048576, 2)}
    except Exception as e:
        return {"error": str(e)}
    return {"avail_gib": 0}

def get_battery():
    try:
        with open("/sys/class/power_supply/battery/capacity", "r") as f:
            capacity = f.read().strip()
        with open("/sys/class/power_supply/battery/status", "r") as f:
            status = f.read().strip()
        return {"level": int(capacity), "status": status}
    except Exception as e:
        return {"level": 0, "status": "Unknown"}

def get_rclone():
    try:
        req = urllib.request.Request(RCLONE_URL, method='POST')
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            speed = data.get('speed', 0)
            transferring = data.get('transferring', [])
            count = len(transferring)
            if count > 0:
                total_bytes = sum(t.get('bytes', 0) for t in transferring if t.get('size', 0) > 0)
                total_size = sum(t.get('size', 0) for t in transferring if t.get('size', 0) > 0)
                percent = int((total_bytes / total_size) * 100) if total_size > 0 else 0
                
                active_files = []
                for t in transferring:
                    size = t.get('size', 0)
                    bytes_sent = t.get('bytes', 0)
                    pct = int((bytes_sent / size) * 100) if size > 0 else 0
                    file_speed = round(t.get('speed', 0) / 1048576, 1)
                    # Extract just the filename if it's a long path
                    name = t.get('name', 'Desconhecido').split('/')[-1]
                    active_files.append({"name": name, "percent": pct, "speed_mb": file_speed})
                    
                return {"speed_mb": round(speed / 1048576, 1), "count": count, "percent": percent, "files": active_files}
            else:
                return {"speed_mb": 0, "count": 0, "percent": 0, "files": []}
    except Exception as e:
        return {"speed_mb": 0, "count": 0, "percent": 0, "files": []}

def get_sys_usage():
    try:
        with open("/proc/loadavg", "r") as f:
            load = float(f.read().split()[0])
            cores = float(os.cpu_count() or 8)
            cpu_percent = round((load / cores) * 100, 1)
            
        output = subprocess.check_output(['/data/data/com.termux/files/usr/bin/free', '-m']).decode('utf-8')
        lines = output.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            total_mb = int(parts[1])
            used_mb = int(parts[2])
            ram_percent = round((used_mb / total_mb) * 100, 1)
            return {"cpu_percent": cpu_percent, "ram_percent": ram_percent, "ram_used": used_mb, "ram_total": total_mb}
    except:
        pass
    return {"cpu_percent": 0, "ram_percent": 0, "ram_used": 0, "ram_total": 0}

def get_backup_logs():
    try:
        log_path = "/data/data/com.termux/files/home/backup_termux.log"
        if not os.path.exists(log_path):
            return {"lines": ["Nenhum backup encontrado ainda."]}
            
        with open(log_path, "r") as f:
            lines = f.readlines()
        return {"lines": [line.strip() for line in lines[-20:]]}
    except Exception as e:
        return {"error": str(e), "lines": [f"Erro ao ler log: {str(e)}"]}

def get_transmission_session_id():
    try:
        req = urllib.request.Request(TRANSMISSION_RPC_URL)
        try:
            urllib.request.urlopen(req, timeout=2)
        except urllib.error.HTTPError as e:
            if e.code == 409:
                return e.headers.get('X-Transmission-Session-Id')
    except Exception:
        pass
    return None

def get_transmission():
    session_id = get_transmission_session_id()
    if not session_id:
        return {"torrents": []}
    
    payload = json.dumps({
        "method": "torrent-get",
        "arguments": {
            "fields": ["id", "name", "hashString", "percentDone", "rateDownload", "rateUpload", "peersConnected", "peersSendingToUs", "status", "eta", "sizeWhenDone", "downloadedEver", "haveValid"]
        }
    }).encode('utf-8')
    
    headers = {
        'X-Transmission-Session-Id': session_id,
        'Content-Type': 'application/json'
    }
    
    try:
        req = urllib.request.Request(TRANSMISSION_RPC_URL, data=payload, headers=headers)
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode())
            torrents = data.get('arguments', {}).get('torrents', [])
            
            STRIKES_FILE = os.path.expanduser("~/.config/transmission-daemon/strikes.json")
            strikes_data = {}
            if os.path.exists(STRIKES_FILE):
                try:
                    with open(STRIKES_FILE, 'r') as f:
                        strikes_data = json.load(f)
                except:
                    pass
            
            def format_size(b):
                if b >= 1000000000: return f"{b/1000000000:.2f} GB"
                elif b >= 1000000: return f"{b/1000000:.2f} MB"
                elif b >= 1000: return f"{b/1000:.2f} KB"
                return f"{int(b)} B"
                
            status_map = {
                0: "Pausado",
                1: "Verificando Fila",
                2: "Verificando",
                3: "Fila",
                4: "Baixando",
                5: "Fila de Envio",
                6: "Seeding"
            }
            active_torrents = []
            for t in torrents:
                pct_raw = t.get('percentDone', 0)
                size_bytes = t.get('sizeWhenDone', 0)
                downloaded_bytes = size_bytes * pct_raw
                
                downloaded_ever = t.get('downloadedEver', 0)
                have_valid = t.get('haveValid', 0)
                is_poisoned = False
                # Regra: Se baixou mais de 200MB E o baixado for 5x maior que o salvo, e tivermos menos de 10%
                if downloaded_ever > 200 * 1048576:
                    if downloaded_ever > (have_valid * 5) and pct_raw < 0.10:
                        is_poisoned = True
                
                t['is_poisoned'] = is_poisoned
                t['strikes'] = strikes_data.get(t.get('hashString', ''), 0)
                t['percentDone'] = round(pct_raw * 100, 1)
                t['rateDownload_mb'] = round(t.get('rateDownload', 0) / 1048576, 1)
                t['size_str'] = f"{format_size(downloaded_bytes)} of {format_size(size_bytes)}"
                t['status_str'] = status_map.get(t.get('status', 0), "Desconhecido")
                
                eta = t.get('eta', -1)
                if t.get('status') == 0:
                    t['eta_str'] = "Pausado"
                elif eta == -1:
                    t['eta_str'] = "Calculando..."
                elif eta > 31536000: # Over a year usually means infinite/stalled
                    t['eta_str'] = "Parado"
                else:
                    m, s = divmod(eta, 60)
                    h, m = divmod(m, 60)
                    d, h = divmod(h, 24)
                    if d > 0:
                        t['eta_str'] = f"{d}d {h}h"
                    elif h > 0:
                        t['eta_str'] = f"{h}h {m}m"
                    else:
                        t['eta_str'] = f"{m}m {s}s"
                        
                active_torrents.append(t)
            
            # --- TMDB/TVDB ID Mappings & Cleanup ---
            MAPPINGS_DIR = os.path.expanduser("~/storage/downloads/Torrent/mappings")
            import time
            if os.path.exists(MAPPINGS_DIR):
                active_hashes = {t.get('hashString', '').lower() for t in torrents if t.get('hashString')}
                current_time = time.time()
                for f in os.listdir(MAPPINGS_DIR):
                    if f.endswith('.txt'):
                        # filename format: <hash>.tmdb.txt or <hash>.tvdb.txt
                        hash_val = f.split('.')[0].lower()
                        txt_path = os.path.join(MAPPINGS_DIR, f)
                        
                        if hash_val in active_hashes:
                            try:
                                with open(txt_path, 'r') as tf:
                                    t_id = tf.read().strip()
                                # find the active torrent and append tmdbId or tvdbId
                                for act in active_torrents:
                                    if act.get('hashString', '').lower() == hash_val:
                                        if '.tmdb.txt' in f:
                                            act['tmdbId'] = t_id
                                        elif '.tvdb.txt' in f:
                                            act['tvdbId'] = t_id
                            except:
                                pass
                        else:
                            # Cleanup old .txt mappings (garbage collection) - Apenas se tiver mais de 7 dias!
                            try:
                                file_age = current_time - os.path.getmtime(txt_path)
                                if file_age > (7 * 24 * 60 * 60):  # 7 dias em segundos
                                    os.remove(txt_path)
                            except:
                                pass
                                
            return {"torrents": active_torrents}
    except Exception as e:
        return {"torrents": [], "error": str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/stats')
def api_stats():
    return jsonify({
        "disk": get_disk_space(),
        "battery": get_battery(),
        "rclone": get_rclone(),
        "transmission": get_transmission(),
        "sys": get_sys_usage(),
        "backup": get_backup_logs()
    })

@app.route('/api/wake-pc', methods=['POST'])
def wake_pc():
    """Envia magic packet WOL via script externo (root + SO_BINDTODEVICE)."""
    import subprocess
    script = '/data/data/com.termux/files/home/wol-pc.py'
    try:
        result = subprocess.run(
            ['/data/data/com.termux/files/usr/bin/python3', script],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            return jsonify({"status": "ok", "message": result.stdout.strip()})
        else:
            return jsonify({"status": "error", "message": result.stderr.strip()}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/pc-status')
def pc_status():
    """Verifica se o PC está online."""
    try:
        from pc_client import get_status
        state = get_status()
        return jsonify({"status": "ok", "pc_state": state})
    except Exception as e:
        return jsonify({"status": "error", "pc_state": "unknown", "message": str(e)})

@app.route('/api/pc-shutdown', methods=['POST'])
def pc_shutdown():
    """Desliga o PC remotamente."""
    try:
        from pc_client import shutdown
        ok, msg = shutdown()
        if ok:
            return jsonify({"status": "ok", "message": "Comando enviado"})
        return jsonify({"status": "error", "message": msg}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/pc-hibernate', methods=['POST'])
def pc_hibernate():
    """Hiberna o PC remotamente."""
    try:
        from pc_client import hibernate
        ok, msg = hibernate()
        if ok:
            return jsonify({"status": "ok", "message": "Comando enviado"})
        return jsonify({"status": "error", "message": msg}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
