#!/data/data/com.termux/files/usr/bin/bash
export PATH=/data/data/com.termux/files/usr/bin:$PATH
export HOME=/data/data/com.termux/files/home

while true; do
  # Agendamento embutido do Backup Semanal (Domingos às 03:00)
  DAY=$(date +%w)
  HOUR=$(date +%H)
  if [ "$DAY" -eq 0 ] && [ "$HOUR" -eq 03 ]; then
    TODAY=$(date +%F)
    if [ ! -f "$HOME/.backup_$TODAY" ]; then
      # Limpar marcadores antigos antes de disparar o backup
      find $HOME -name ".backup_*" -mtime +2 -exec rm {} \; 2>/dev/null
      touch "$HOME/.backup_$TODAY"
      bash $HOME/backup_termux.sh &
    fi
  fi

  bash $HOME/worker.sh
  python3 $HOME/queue_manager.py
  sleep 120
done
