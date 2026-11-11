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

# ==============================================================================
# 1. EXTRAÇÃO DE ARQUIVOS COMPACTADOS (.7z, .rar, .zip, etc.)
# ==============================================================================
EXT="${CAMINHO_DO_ARQUIVO##*.}"
EXT_LOWER=$(echo "$EXT" | tr '[:upper:]' '[:lower:]')

if [ -f "$CAMINHO_DO_ARQUIVO" ]; then
    if [[ "$EXT_LOWER" =~ ^(7z|rar|zip|tar|gz|bz2|xz)$ ]]; then
        EXTRACT_DIR="${CAMINHO_DO_ARQUIVO%.*}"
        mkdir -p "$EXTRACT_DIR"
        echo "[$(date)] Arquivo compactado detectado: $CAMINHO_DO_ARQUIVO. Extraindo com 7z..." >> $HOME/upload_gdrive.log
        if 7z x -y -p- "$CAMINHO_DO_ARQUIVO" -o"$EXTRACT_DIR" >> $HOME/upload_gdrive.log 2>&1; then
            echo "[$(date)] Extração concluída. Removendo arquivo compactado original..." >> $HOME/upload_gdrive.log
            rm -f "$CAMINHO_DO_ARQUIVO"
            CAMINHO_DO_ARQUIVO="$EXTRACT_DIR"
            TR_TORRENT_NAME="$(basename "$EXTRACT_DIR")"
        else
            echo "[$(date)] ERRO ao extrair $CAMINHO_DO_ARQUIVO (corrompido ou protegido por senha)." >> $HOME/upload_gdrive.log
        fi
    fi
elif [ -d "$CAMINHO_DO_ARQUIVO" ]; then
    ARCHIVES=$(find "$CAMINHO_DO_ARQUIVO" -type f \( -iname "*.7z" -o -iname "*.rar" -o -iname "*.zip" \) 2>/dev/null)
    if [ -n "$ARCHIVES" ]; then
        echo "[$(date)] Arquivos compactados encontrados na pasta $CAMINHO_DO_ARQUIVO. Extraindo..." >> $HOME/upload_gdrive.log
        while IFS= read -r arch; do
            [ -f "$arch" ] || continue
            DIR_ARCH=$(dirname "$arch")
            if 7z x -y -p- "$arch" -o"$DIR_ARCH" >> $HOME/upload_gdrive.log 2>&1; then
                rm -f "$arch"
            fi
        done <<< "$ARCHIVES"
    fi
fi

# ==============================================================================
# 2. VALIDAÇÃO DE VÍDEO LEGÍTIMO E ELIMINAÇÃO DE FALSOS / MALWARE
# ==============================================================================
VIDEOS=$(find "$CAMINHO_DO_ARQUIVO" -type f \( -iname "*.mkv" -o -iname "*.mp4" -o -iname "*.avi" -o -iname "*.ts" -o -iname "*.m4v" -o -iname "*.webm" \) 2>/dev/null)

if [ -z "$VIDEOS" ]; then
    echo "[$(date)] [FALHA] Nenhum arquivo de vídeo legítimo encontrado em: $CAMINHO_DO_ARQUIVO" >> $HOME/upload_gdrive.log
    echo "[$(date)] Reportando falha ao Sonarr/Radarr para auto-redownload e blocklist..." >> $HOME/upload_gdrive.log
    
    if [ -n "$HASH" ]; then
        python3 "$HOME/queue_manager.py" --report-fail "$HASH" "$TR_TORRENT_NAME" >> $HOME/upload_gdrive.log 2>&1
    fi
    
    if [ -n "$TR_TORRENT_ID" ]; then
        transmission-remote -t "$TR_TORRENT_ID" --remove-and-delete >> $HOME/upload_gdrive.log 2>&1
    fi
    rm -rf "$CAMINHO_DO_ARQUIVO"
    exit 0
fi

# Limpar arquivos executáveis maliciosos que possam ter vindo junto
find "$CAMINHO_DO_ARQUIVO" -type f \( -iname "*.exe" -o -iname "*.bat" -o -iname "*.cmd" -o -iname "*.scr" -o -iname "*.lnk" -o -iname "*.url" \) -delete 2>/dev/null

DESTINO_FINAL="$DESTINO_GDRIVE/$TARGET_FOLDER"

echo "[$(date)] Iniciando upload de: $TR_TORRENT_NAME -> $TARGET_FOLDER (Bypass de VPN via SOCKS5)" >> $HOME/upload_gdrive.log

if HTTPS_PROXY=socks5://127.0.0.1:1081 flock $HOME/upload.lock rclone move "$CAMINHO_DO_ARQUIVO" "$DESTINO_FINAL" -P --transfers=4 --checkers=8 --drive-chunk-size=64M --multi-thread-streams=8 --multi-thread-cutoff=64M --local-no-check-updated --rc --rc-addr localhost:5575 --rc-no-auth --contimeout 15s --timeout 60s --log-file="$HOME/upload_gdrive.log"; then
    echo "[$(date)] Upload concluido para: $DESTINO_FINAL" >> $HOME/upload_gdrive.log
    transmission-remote -t "$TR_TORRENT_ID" -r
    [ -d "$CAMINHO_DO_ARQUIVO" ] && rm -rf "$CAMINHO_DO_ARQUIVO"
else
    echo "[$(date)] ERRO no upload de: $TR_TORRENT_NAME. Torrent mantido no Transmission." >> $HOME/upload_gdrive.log
fi
