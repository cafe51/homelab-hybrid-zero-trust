#!/data/data/com.termux/files/usr/bin/bash

export PATH=/data/data/com.termux/files/usr/bin:$PATH
export HOME=/data/data/com.termux/files/home

DESTINO_GDRIVE="gdrive:Blackhole/Downloads_Concluidos"
CAMINHO_DO_ARQUIVO="$TR_TORRENT_DIR/$TR_TORRENT_NAME"

if [ -z "$CAMINHO_DO_ARQUIVO" ] || [ -z "$TR_TORRENT_NAME" ]; then
    echo "Erro: Parametros faltando." >> $HOME/upload_gdrive.log
    exit 1
fi

if [ ! -e "$CAMINHO_DO_ARQUIVO" ]; then
    echo "[$(date)] Arquivo $TR_TORRENT_NAME nao encontrado localmente (ja movido?). Removendo do Transmission." >> $HOME/upload_gdrive.log
    transmission-remote -t "$TR_TORRENT_ID" -r
    exit 0
fi

# Obter Hash do torrent para consultar mapeamentos limpos (TMDB/Title)
HASH="${TR_TORRENT_HASH:-}"
if [ -z "$HASH" ] && [ -n "$TR_TORRENT_ID" ]; then
    HASH=$(transmission-remote -t "$TR_TORRENT_ID" -i 2>/dev/null | grep -i "Hash:" | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
fi

TARGET_FOLDER=""
if [ -n "$HASH" ] && [ -f "$HOME/storage/downloads/Torrent/mappings/$HASH.title.txt" ]; then
    CLEAN_TITLE=$(head -n 1 "$HOME/storage/downloads/Torrent/mappings/$HASH.title.txt" | tr -d '\r\n')
    if [ -n "$CLEAN_TITLE" ]; then
        TARGET_FOLDER="$CLEAN_TITLE"
    fi
fi

# Fallback se não houver mapeamento de título
if [ -z "$TARGET_FOLDER" ]; then
    if [ -d "$CAMINHO_DO_ARQUIVO" ]; then
        TARGET_FOLDER="$TR_TORRENT_NAME"
    else
        TARGET_FOLDER="${TR_TORRENT_NAME%.*}"
    fi
fi

DESTINO_FINAL="$DESTINO_GDRIVE/$TARGET_FOLDER"

echo "[$(date)] Iniciando upload de: $TR_TORRENT_NAME -> $TARGET_FOLDER (Bypass de VPN via SOCKS5)" >> $HOME/upload_gdrive.log

if HTTPS_PROXY=socks5://127.0.0.1:1081 flock $HOME/upload.lock rclone move "$CAMINHO_DO_ARQUIVO" "$DESTINO_FINAL" -P --transfers=4 --checkers=8 --drive-chunk-size=64M --multi-thread-streams=8 --multi-thread-cutoff=64M --local-no-check-updated --rc --rc-addr localhost:5575 --rc-no-auth --contimeout 15s --timeout 60s --log-file="$HOME/upload_gdrive.log"; then
    echo "[$(date)] Upload concluido para: $DESTINO_FINAL" >> $HOME/upload_gdrive.log
    transmission-remote -t "$TR_TORRENT_ID" -r
else
    echo "[$(date)] ERRO no upload de: $TR_TORRENT_NAME. Torrent mantido no Transmission." >> $HOME/upload_gdrive.log
fi
