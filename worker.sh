#!/data/data/com.termux/files/usr/bin/bash
export PATH=/data/data/com.termux/files/usr/bin:$PATH
export HOME=/data/data/com.termux/files/home
DIR_MAGNETS="$HOME/storage/downloads/Torrent/magnets"
DIR_STAGING="$HOME/storage/downloads/Torrent/staging"
DIR_MAPPINGS="$HOME/storage/downloads/Torrent/mappings"

mkdir -p "$DIR_MAGNETS" "$DIR_STAGING" "$DIR_MAPPINGS"

echo "[$(date)] Sincronizando magnets e mapeamentos..."
rclone move gdrive:Blackhole/Fila_Downloads "$DIR_STAGING" --include "*.magnet" --include "*.torrent" --include "*.txt" --ignore-existing --contimeout 15s --timeout 30s

for f in "$DIR_STAGING"/*.magnet "$DIR_STAGING"/*.torrent; do
    if [ -f "$f" ]; then
        # Extrair Hash
        if [[ "$f" == *.magnet ]]; then
            HASH=$(python3 -c 'import sys,re,base64; m=re.search(r"urn:btih:([a-zA-Z0-9]+)", open(sys.argv[1]).read()); h=m.group(1).lower() if m else ""; print(base64.b32decode(h.upper()).hex().lower() if len(h)==32 else h)' "$f" 2>/dev/null)
        else
            HASH=$(transmission-show "$f" 2>/dev/null | grep -i "Hash:" | awk '{print $2}' | tr '[:upper:]' '[:lower:]')
        fi
        
        BASENAME="${f%.*}"
        if [ -n "$HASH" ]; then
            if [ -f "${BASENAME}.tmdb.txt" ]; then
                mv "${BASENAME}.tmdb.txt" "$DIR_MAPPINGS/$HASH.tmdb.txt"
            fi
            if [ -f "${BASENAME}.tvdb.txt" ]; then
                mv "${BASENAME}.tvdb.txt" "$DIR_MAPPINGS/$HASH.tvdb.txt"
            fi
        fi
        
        # Mover magnet final
        UNIQUE_NAME="$(date +%s)_$(basename "$f")"
        mv "$f" "$DIR_MAGNETS/$UNIQUE_NAME"
    fi
done

# Limpeza caso algum txt tenha ficado orfão sem magnet correspondente
rm -f "$DIR_STAGING"/*.txt
