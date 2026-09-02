#!/data/data/com.termux/files/usr/bin/bash
export PATH=/data/data/com.termux/files/usr/bin:$PATH
export HOME=/data/data/com.termux/files/home

LOG_FILE="$HOME/backup_termux.log"
DATE_STR=$(date +%Y-%m-%d_%H-%M)
BACKUP_FILENAME="termux-snapshot-${DATE_STR}.tar.gz"
BACKUP_TEMP_PATH="/sdcard/Download/$BACKUP_FILENAME"
GDRIVE_DEST="gdrive:Blackhole/Backups_Termux"

echo "========================================" >> "$LOG_FILE"
echo "[$(date)] Iniciando Backup Total do Termux (Snapshot)" >> "$LOG_FILE"

# 1. Empacotar usr e home (diretórios absolutos da raiz do Termux)
echo "[$(date)] Compactando sistema em $BACKUP_TEMP_PATH..." >> "$LOG_FILE"
tar \
    --exclude='./home/storage' \
    --exclude='./home/*.log' \
    --exclude='./home/.backup_*' \
    --exclude='./home/.cache' \
    --exclude='*.sock' \
    --exclude='*.sock*' \
    --warning=no-file-changed \
    --warning=no-file-removed \
    --ignore-failed-read \
    -zcf "$BACKUP_TEMP_PATH" \
    -C /data/data/com.termux/files ./home ./usr 2>> "$LOG_FILE"
TAR_RC=$?

if [ $TAR_RC -eq 0 ] || [ $TAR_RC -eq 1 ]; then
    echo "[$(date)] Compactação concluída com sucesso (status: $TAR_RC)." >> "$LOG_FILE"
else
    echo "[$(date)] ERRO: Falha na compactação do sistema (status: $TAR_RC). Abortando upload." >> "$LOG_FILE"
    rm -f "$BACKUP_TEMP_PATH"
    exit 1
fi

# 2. Fazer upload pro Google Drive via rclone
echo "[$(date)] Iniciando upload para $GDRIVE_DEST..." >> "$LOG_FILE"
if rclone move "$BACKUP_TEMP_PATH" "$GDRIVE_DEST" -P --transfers=4 --checkers=4 --contimeout 15s --timeout 60s --log-file="$LOG_FILE" --log-level INFO; then
    echo "[$(date)] Upload concluído com sucesso." >> "$LOG_FILE"
else
    echo "[$(date)] ERRO: Falha no upload para o Google Drive." >> "$LOG_FILE"
    # Tenta remover o arquivo local para não estourar o disco
    rm -f "$BACKUP_TEMP_PATH"
    exit 1
fi

# 3. Faxina (Remover backups antigos da nuvem - mantendo 30 dias de histórico)
echo "[$(date)] Limpando backups mais antigos que 30 dias na nuvem..." >> "$LOG_FILE"
rclone delete "$GDRIVE_DEST" --min-age 30d --log-file="$LOG_FILE" --log-level INFO
echo "[$(date)] Faxina concluída." >> "$LOG_FILE"

echo "[$(date)] Backup Finalizado com Êxito." >> "$LOG_FILE"
