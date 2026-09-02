#!/data/data/com.termux/files/usr/bin/bash
# ==============================================================================
# Script de Inicialização Root: Proxy Residencial SOCKS5 & Dashboard de Telemetria
# ==============================================================================
# Executa socks5.py e app.py como Root no Android para acesso a sockets de baixo nível (SO_BINDTODEVICE)
# e leitura de sensores de hardware do kernel (/sys/class/power_supply/battery).

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="/data/data/com.termux/files/usr/bin/python3"

echo "[$(date)] Iniciando serviços Root do Edge Worker..."

# 1. Iniciar Proxy Residencial SOCKS5
su -c "nohup $PYTHON_BIN $DIR/socks5.py > $DIR/socks5.log 2>&1 &"

# 2. Iniciar Dashboard Flask com telemetria
su -c "nohup $PYTHON_BIN $DIR/app.py > $DIR/app.log 2>&1 &"

# 3. Ajustar permissões de leitura dos sensores de bateria do kernel
su -c 'chmod 644 /sys/class/power_supply/battery/capacity /sys/class/power_supply/battery/status 2>/dev/null || true'

# 4. Ajustar SELinux para modo permissivo (necessário para ler sysfs e sockets no Android root)
su -c 'setenforce 0 2>/dev/null || true'

echo "[$(date)] Serviços Root inicializados com sucesso."
