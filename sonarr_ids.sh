#!/bin/bash
BLACKHOLE_DIR="/home/ubuntu/GoogleDrive/Blackhole/Fila_Downloads"
if [ -n "$sonarr_release_title" ]; then
    if [ -n "$sonarr_series_tvdbid" ]; then
        echo "$sonarr_series_tvdbid" > "$BLACKHOLE_DIR/$sonarr_release_title.tvdb.txt"
    fi
    if [ -n "$sonarr_series_tmdbid" ]; then
        echo "$sonarr_series_tmdbid" > "$BLACKHOLE_DIR/$sonarr_release_title.tmdb.txt"
    fi
fi
