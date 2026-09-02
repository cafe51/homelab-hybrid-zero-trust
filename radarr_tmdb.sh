#!/bin/bash
BLACKHOLE_DIR="/home/ubuntu/GoogleDrive/Blackhole/Fila_Downloads"
if [ -n "$radarr_release_title" ] && [ -n "$radarr_movie_tmdbid" ]; then
    echo "$radarr_movie_tmdbid" > "$BLACKHOLE_DIR/$radarr_release_title.tmdb.txt"
fi
