#!/data/data/com.termux/files/usr/bin/bash

export PATH=/data/data/com.termux/files/usr/bin:$PATH
export HOME=/data/data/com.termux/files/home

DESTINO_GDRIVE="gdrive:Blackhole/Downloads_Concluidos"
CAMINHO_DO_ARQUIVO="$TR_TORRENT_DIR/$TR_TORRENT_NAME"

if [ -z "$CAMINHO_DO_ARQUIVO" ] || [ -z "$TR_TORRENT_NAME" ]; then
    echo "Erro: Parametros faltando." >> $HOME/upload_gdrive.log
    exit 1
fi

echo "[$(date)] Iniciando upload de: $TR_TORRENT_NAME (Bypass de VPN via SOCKS5)" >> $HOME/upload_gdrive.log

if HTTPS_PROXY=socks5://127.0.0.1:1081 flock $HOME/upload.lock rclone move "$CAMINHO_DO_ARQUIVO" "$DESTINO_GDRIVE/$TR_TORRENT_NAME" -P --transfers=4 --checkers=8 --drive-chunk-size=64M --multi-thread-streams=8 --multi-thread-cutoff=64M --local-no-check-updated --rc --rc-addr localhost:5575 --rc-no-auth --contimeout 15s --timeout 60s --log-file="$HOME/upload_gdrive.log"; then
    echo "[$(date)] Upload concluido para: $DESTINO_GDRIVE/$TR_TORRENT_NAME" >> $HOME/upload_gdrive.log
    transmission-remote -t "$TR_TORRENT_ID" -r
else
    echo "[$(date)] ERRO no upload de: $TR_TORRENT_NAME. Torrent mantido no Transmission." >> $HOME/upload_gdrive.log
fi
