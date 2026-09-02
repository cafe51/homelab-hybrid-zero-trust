#!/system/bin/sh
export PREFIX=/data/data/com.termux/files/usr
export LD_LIBRARY_PATH=$PREFIX/lib
export PATH=$PREFIX/bin:$PATH

echo "Restoring home folder..."
cp -r /sdcard/Download/TermuxBackup/.ssh $PREFIX/../home/.ssh/ 2>/dev/null
cp -r /sdcard/Download/TermuxBackup/.config $PREFIX/../home/.config/ 2>/dev/null
cp -r /sdcard/Download/TermuxBackup/.termux $PREFIX/../home/.termux/ 2>/dev/null
cp /sdcard/Download/TermuxBackup/*.sh $PREFIX/../home/ 2>/dev/null
cp /sdcard/Download/TermuxBackup/*.py $PREFIX/../home/ 2>/dev/null
cp -r /sdcard/Download/TermuxBackup/templates $PREFIX/../home/ 2>/dev/null
chmod +x $PREFIX/../home/*.sh $PREFIX/../home/*.py


echo "Installing packages..."
yes | pkg update
yes | pkg install openssh python transmission tailscale rclone tmux termux-services jq

echo "Installing anti-zombie wrapper..."
cp $PREFIX/bin/transmission-daemon $PREFIX/bin/transmission-daemon.bin
cp $PREFIX/../home/transmission-wrapper.sh $PREFIX/bin/transmission-daemon
chmod +x $PREFIX/bin/transmission-daemon

echo "Installing python packages..."
pip install flask requests

echo "Starting services..."
termux-wake-lock
$PREFIX/../home/.termux/boot/start-proxy
$PREFIX/../home/start_servers.sh
