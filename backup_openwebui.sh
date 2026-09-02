#!/bin/bash
CONFIG_DIR="/home/ubuntu/configs/open-webui"
BACKUP_DIR="/home/ubuntu/backups"
RCLONE_DEST="gdrive:Homelab_Backups/OpenWebUI"
DATE=$(date +%F_%H-%M)
ARCHIVE_NAME="openwebui_backup_${DATE}.tar.gz"

echo "======================================"
echo "Iniciando Backup do OpenWebUI: $DATE"
echo "======================================"

mkdir -p "$BACKUP_DIR"

echo "Parando o conteiner open-webui..."
cd /home/ubuntu/configs || exit 1
docker compose stop open-webui

echo "Compactando a pasta de configuracoes..."
cd /home/ubuntu/configs || exit 1
tar -czvf "$BACKUP_DIR/$ARCHIVE_NAME" open-webui/

echo "Religando o conteiner open-webui..."
cd /home/ubuntu/configs || exit 1
docker compose start open-webui

echo "Enviando para o Google Drive..."
rclone copy "$BACKUP_DIR/$ARCHIVE_NAME" "$RCLONE_DEST"

if [ $? -eq 0 ]; then
    echo "Upload concluido com sucesso."
    echo "Limpando backup local..."
    rm "$BACKUP_DIR/$ARCHIVE_NAME"
    echo "Limpando backups antigos no Google Drive (> 7 dias)..."
    rclone delete --min-age 7d "$RCLONE_DEST"
    echo "Backup finalizado com Sucesso!"
else
    echo "ERRO no upload do backup para o Google Drive."
    exit 1
fi
