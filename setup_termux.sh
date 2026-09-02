#!/data/data/com.termux/files/usr/bin/bash

# Define environment for Termux
export PREFIX=/data/data/com.termux/files/usr
export HOME=/data/data/com.termux/files/home
export LD_LIBRARY_PATH=/data/data/com.termux/files/usr/lib
export PATH=/data/data/com.termux/files/usr/bin:$PATH

cd $HOME

echo "Checking Termux Storage..."
if [ ! -d "$HOME/storage" ]; then
    echo "Storage not mounted. Attempting termux-setup-storage..."
    # termux-setup-storage needs UI interaction usually, but let's see if it's already there
    termux-setup-storage
    sleep 2
fi
ls -l $HOME/storage/downloads || echo "Warning: Storage not accessible."

echo "Updating repositories and installing packages..."
pkg update -y
pkg upgrade -y
pkg install -y openssh python transmission tailscale rclone tmux termux-services jq

echo "Installing python packages..."
pip install flask requests

echo "Checking installed versions:"
rclone version
transmission-daemon --version
python --version

echo "Creating download directories in storage..."
mkdir -p $HOME/storage/downloads/Torrent/completo
mkdir -p $HOME/storage/downloads/Torrent/incompleto

echo "Setup completed."
