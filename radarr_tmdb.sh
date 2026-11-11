#!/bin/bash
BLACKHOLE_DIR="/home/ubuntu/GoogleDrive/Blackhole/Fila_Downloads"
if [ -n "$radarr_release_title" ]; then
    if [ -n "$radarr_movie_tmdbid" ]; then
        echo "$radarr_movie_tmdbid" > "$BLACKHOLE_DIR/$radarr_release_title.tmdb.txt"
    fi
    if [ -n "$radarr_movie_title" ] && [ -n "$radarr_movie_year" ]; then
        echo "$radarr_movie_title ($radarr_movie_year)" > "$BLACKHOLE_DIR/$radarr_release_title.title.txt"
    fi
fi
