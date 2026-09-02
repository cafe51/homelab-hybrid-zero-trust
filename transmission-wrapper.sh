#!/data/data/com.termux/files/usr/bin/bash

# Anti-Zombie Wrapper
echo "[$(date)] wrapper started." >> /data/data/com.termux/files/home/transmission-wrapper.log

# Pega todos os PIDs que contêm transmission-daemon
PIDS=$(pgrep -f "transmission-daemon")

# Remove o PID atual ($$) da lista para não suicidar
PIDS_TO_KILL=""
for pid in $PIDS; do
    if [ "$pid" != "$$" ]; then
        PIDS_TO_KILL="$PIDS_TO_KILL $pid"
    fi
done

if [ -n "$PIDS_TO_KILL" ]; then
    echo "[$(date)] Zumbis detectados: $PIDS_TO_KILL. Matando..." >> /data/data/com.termux/files/home/transmission-wrapper.log
    kill -9 $PIDS_TO_KILL 2>/dev/null
    sleep 1
fi

exec /data/data/com.termux/files/usr/bin/transmission-daemon.bin "$@"
