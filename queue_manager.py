#!/usr/bin/env python3
import json
import urllib.request
import urllib.error
import subprocess
import time
import os
import concurrent.futures

def load_env():
    """Carrega variáveis de ambiente de arquivos .env locais se existirem."""
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

TRANSMISSION_RPC_URL = os.getenv("TRANSMISSION_RPC_URL", "http://localhost:9091/transmission/rpc")
SAFETY_MARGIN_GB = int(os.getenv("SAFETY_MARGIN_GB", "4"))
STALLED_MINUTES = int(os.getenv("STALLED_MINUTES", "5"))
STRIKES_FILE = os.path.expanduser("~/.config/transmission-daemon/strikes.json")

RADARR_URL = os.getenv("RADARR_URL", "http://localhost:7878")
RADARR_API_KEY = os.getenv("RADARR_API_KEY", "")
SONARR_URL = os.getenv("SONARR_URL", "http://localhost:8989")
SONARR_API_KEY = os.getenv("SONARR_API_KEY", "")

def load_strikes():
    if os.path.exists(STRIKES_FILE):
        try:
            with open(STRIKES_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError, OSError):
            pass
    return {}

def save_strikes(strikes):
    os.makedirs(os.path.dirname(STRIKES_FILE), exist_ok=True)
    with open(STRIKES_FILE, 'w') as f:
        json.dump(strikes, f)

def get_disk_free_bytes():
    output = subprocess.check_output(['df', '-k', '/data']).decode('utf-8')
    lines = output.strip().split('\n')
    if len(lines) >= 2:
        parts = lines[1].split()
        avail_kb = int(parts[3])
        return avail_kb * 1024
    return 0

def is_upload_running():
    try:
        res = subprocess.run(
            ['flock', '-n', os.path.expanduser('~/upload.lock'), 'true'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return res.returncode != 0
    except Exception:
        return False

def get_transmission_session_id():
    req = urllib.request.Request(TRANSMISSION_RPC_URL)
    try:
        urllib.request.urlopen(req, timeout=5)
    except urllib.error.HTTPError as e:
        if e.code == 409:
            return e.headers.get('X-Transmission-Session-Id')
    return None

def call_transmission_rpc(method, arguments=None):
    session_id = get_transmission_session_id()
    if not session_id:
        return None
    
    payload = {"method": method}
    if arguments:
        payload["arguments"] = arguments
        
    req = urllib.request.Request(TRANSMISSION_RPC_URL, data=json.dumps(payload).encode('utf-8'), headers={
        'X-Transmission-Session-Id': session_id,
        'Content-Type': 'application/json'
    })
    
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None

def pause_torrents(torrent_ids):
    if torrent_ids:
        call_transmission_rpc("torrent-stop", {"ids": torrent_ids})
        print(f"Pausado: {torrent_ids}")

def resume_torrents(torrent_ids):
    if torrent_ids:
        call_transmission_rpc("torrent-start", {"ids": torrent_ids})
        print(f"Resumido: {torrent_ids}")

def call_arr_api(app_url, api_key, method, endpoint, data=None):
    url = f"{app_url}{endpoint}"
    cmd = [
        "curl", "-s", "--connect-timeout", "10", "--max-time", "30",
        "-x", "socks5h://127.0.0.1:1055",
        "-X", method,
        "-H", f"X-Api-Key: {api_key}",
        "-H", "Content-Type: application/json"
    ]
    if data:
        cmd.extend(["-d", json.dumps(data)])
    cmd.append(url)
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode('utf-8')
        if output:
            return json.loads(output)
    except Exception:
        pass
    return None

def report_failure_to_arr(name, hash_string):
    hash_lower = hash_string.lower()
    
    def check_and_report(app_url, api_key, app_name):
        history = call_arr_api(app_url, api_key, "GET", "/api/v3/history?eventType=grabbed&pageSize=200")
        if history and 'records' in history:
            for record in history['records']:
                r_hash = record.get('data', {}).get('torrentInfoHash', '').lower()
                if r_hash and r_hash == hash_lower:
                    call_arr_api(app_url, api_key, "POST", f"/api/v3/history/failed/{record['id']}")
                    print(f"[{app_name}] Falha reportada (Hash Match) e blocklisted para: {name}")
                    return True
        return False

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f_radarr = executor.submit(check_and_report, RADARR_URL, RADARR_API_KEY, "RADARR")
        f_sonarr = executor.submit(check_and_report, SONARR_URL, SONARR_API_KEY, "SONARR")
        
        # Espera as duas terminarem; se qualquer uma achar, consideramos sucesso
        found_radarr = f_radarr.result()
        found_sonarr = f_sonarr.result()

    if not found_radarr and not found_sonarr:
        print(f"[AVISO] Não foi possível encontrar o Hash {hash_string} ({name}) no histórico.")
        return False
    return True

def main():
    free_bytes = get_disk_free_bytes()
    if free_bytes == 0:
        return
        
    budget_bytes = free_bytes - (SAFETY_MARGIN_GB * 1024 * 1024 * 1024)
    if budget_bytes < 0:
        budget_bytes = 0

    data = call_transmission_rpc("torrent-get", {
        "fields": ["id", "name", "hashString", "magnetLink", "status", "leftUntilDone", "rateDownload", "addedDate", "activityDate", "percentDone", "startDate", "downloadedEver", "haveValid", "doneDate", "downloadDir"]
    })
    
    if not data or 'arguments' not in data or 'torrents' not in data['arguments']:
        return

    torrents = data['arguments']['torrents']
    current_time = time.time()
    
    downloading = []
    paused_or_queued = []
    
    # Processamento e Filtragem
    for t in torrents:
        if t['leftUntilDone'] > 0:
            downloaded_ever = t.get('downloadedEver', 0)
            have_valid = t.get('haveValid', 0)
            pct_raw = t.get('percentDone', 0)
            
            # 0. POISONED SWARM DETECTION
            if downloaded_ever > 200 * 1048576 and downloaded_ever > (have_valid * 5) and pct_raw < 0.10:
                strikes = load_strikes()
                hash_str = t['hashString']
                current_strikes = strikes.get(hash_str, 0)
                
                if current_strikes < 2:
                    current_strikes += 1
                    strikes[hash_str] = current_strikes
                    save_strikes(strikes)
                    print(f"Poisoned swarm detectado: {t['name']}. Strike {current_strikes}/3. Reiniciando torrent (Amnésia local)...")
                    call_transmission_rpc("torrent-remove", {"ids": [t['id']], "delete-local-data": True})
                    call_transmission_rpc("torrent-add", {"filename": t['magnetLink']})
                else:
                    print(f"Poisoned swarm detectado: {t['name']}. Strike 3/3 atingido! Iniciando Fail definitivo no Radarr...")
                    report_failure_to_arr(t['name'], hash_str)
                    call_transmission_rpc("torrent-remove", {"ids": [t['id']], "delete-local-data": True})
                    if hash_str in strikes:
                        del strikes[hash_str]
                        save_strikes(strikes)
                continue
                
            if t['status'] in [3, 4]: # Downloading or Download Wait
                downloading.append(t)
            elif t['status'] == 0: # Stopped
                paused_or_queued.append(t)
    
    # 1. TRATAMENTO DE TORRENTS TRAVADOS (STALLED)
    to_pause_stalled = []
    healthy_downloading = []
    for t in downloading:
        stalled_time_secs = STALLED_MINUTES * 60
        time_since_add = current_time - t['addedDate']
        
        # Determine last activity (use addedDate if activityDate is 0)
        last_activity = t['activityDate'] if t['activityDate'] > 0 else t['addedDate']
        time_since_activity = current_time - last_activity
        
        # Determine time since last started
        time_since_start = current_time - t['startDate'] if t.get('startDate', 0) > 0 else 0
        
        # If rate is 0, no activity for STALLED_MINUTES, and running for STALLED_MINUTES, it's stalled
        if t['rateDownload'] == 0 and time_since_activity > stalled_time_secs and time_since_add > stalled_time_secs and time_since_start > stalled_time_secs:
            to_pause_stalled.append(t['id'])
        else:
            healthy_downloading.append(t)
            
    if to_pause_stalled:
        print(f"Congelando torrents sem seed (Stalled): {to_pause_stalled}")
        pause_torrents(to_pause_stalled)
        
    # 2. CÁLCULO DA DÍVIDA ATIVA
    active_debt = sum(t['leftUntilDone'] for t in healthy_downloading)
    
    # 3. PROTEÇÃO CONTRA ESTOURO DE DISCO (OVERFLOW)
    if active_debt > budget_bytes:
        # Sort healthy downloading: pause the newest added or lowest speed first
        # We sort by speed ascending (slowest paused first)
        healthy_downloading.sort(key=lambda x: x['rateDownload'])
        
        to_pause_overflow = []
        for t in healthy_downloading:
            if active_debt <= budget_bytes:
                break
            to_pause_overflow.append(t['id'])
            active_debt -= t['leftUntilDone']
            
        if to_pause_overflow:
            print(f"Orçamento estourado! Pausando excedentes: {to_pause_overflow}")
            pause_torrents(to_pause_overflow)
            
    # 4. INÍCIO DINÂMICO (RESUME)
    elif active_debt < budget_bytes:
        # Sort paused torrents by addedDate (oldest first)
        paused_or_queued.sort(key=lambda x: x['addedDate'])
        
        to_resume = []
        for t in paused_or_queued:
            if active_debt + t['leftUntilDone'] <= budget_bytes:
                to_resume.append(t['id'])
                active_debt += t['leftUntilDone']
                
        if to_resume:
            print(f"Orçamento livre! Iniciando fila inteligente: {to_resume}")
            resume_torrents(to_resume)

    # 5. WATCHDOG: RECOVERY DE TORRENTS CONCLUÍDOS NÃO ENVIADOS (STUCK/SEEDING)
    completed_stuck = []
    for t in torrents:
        if t['leftUntilDone'] == 0 or t.get('percentDone', 0) >= 1.0:
            done_date = t.get('doneDate', 0)
            if done_date > 0 and (current_time - done_date) > 300:
                completed_stuck.append(t)

    if completed_stuck and not is_upload_running():
        stuck = completed_stuck[0]
        torrent_dir = stuck.get('downloadDir', os.path.expanduser('~/storage/downloads/Torrent/completo'))
        torrent_name = stuck['name']
        torrent_id = str(stuck['id'])
        print(f"Watchdog: Torrent concluído sem upload detectado: {torrent_name} (ID: {torrent_id}). Acionando upload_gdrive.sh...")
        env = os.environ.copy()
        env['TR_TORRENT_DIR'] = torrent_dir
        env['TR_TORRENT_NAME'] = torrent_name
        env['TR_TORRENT_ID'] = torrent_id
        env['TR_TORRENT_HASH'] = stuck.get('hashString', '')
        upload_script = os.path.expanduser('~/upload_gdrive.sh')
        if os.path.exists(upload_script):
            subprocess.Popen(['bash', upload_script], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Erro no Queue Manager: {e}")
