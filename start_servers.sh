#!/data/data/com.termux/files/usr/bin/bash

export PATH=/data/data/com.termux/files/usr/bin:$PATH
export HOME=/data/data/com.termux/files/home

echo "=== Verificando Servidores do Worker ==="

if ! pgrep -x "sshd" >/dev/null; then
    echo "[+] Iniciando SSHD..."
    sshd
fi

if ! pgrep -x "tailscaled" >/dev/null; then
    echo "[+] Iniciando Tailscale..."
    tmux new-session -d -s tailscale "tailscaled --tun=userspace-networking --socks5-server=localhost:1055 --statedir=$HOME/.local/share/tailscale --socket=$HOME/tailscaled.sock"
fi

if ! pgrep -f "transmission-daemon" >/dev/null; then
    echo "[+] Iniciando Transmission..."
    transmission-daemon --download-dir $HOME/storage/downloads/Torrent/completo --incomplete-dir $HOME/storage/downloads/Torrent/incompleto --watch-dir $HOME/storage/downloads/Torrent/magnets
fi

if ! pgrep -f "app.py" >/dev/null || ! pgrep -f "socks5.py" >/dev/null; then
    echo "[+] Iniciando Proxy Residencial e Telemetria..."
    if [ -f "$HOME/start-proxy.sh" ]; then
        bash "$HOME/start-proxy.sh"
    elif [ -f "$HOME/.termux/boot/start-proxy" ]; then
        bash "$HOME/.termux/boot/start-proxy"
    elif [ -f "./start-proxy.sh" ]; then
        bash "./start-proxy.sh"
    else
        python3 "$HOME/socks5.py" &
        python3 "$HOME/app.py" &
    fi
fi

if ! tmux has-session -t worker 2>/dev/null; then
    echo "[+] Iniciando automação do Worker..."
    tmux new-session -d -s worker bash $HOME/loop.sh
fi

termux-wake-lock 2>/dev/null || true
echo "=== Todos os sistemas operacionais! ==="
