echo "Restoring home folder..."
cp -r /sdcard/Download/TermuxBackup/.ssh ~/.ssh/ 2>/dev/null
cp -r /sdcard/Download/TermuxBackup/.config ~/.config/ 2>/dev/null
cp -r /sdcard/Download/TermuxBackup/.termux ~/.termux/ 2>/dev/null
cp /sdcard/Download/TermuxBackup/*.sh ~/ 2>/dev/null
cp /sdcard/Download/TermuxBackup/*.py ~/ 2>/dev/null
cp -r /sdcard/Download/TermuxBackup/templates ~/ 2>/dev/null
chmod +x ~/*.sh ~/*.py


echo "Installing packages..."
yes | pkg update
yes | pkg install openssh python transmission tailscale rclone tmux termux-services jq

echo "Installing anti-zombie wrapper..."
cp $PREFIX/bin/transmission-daemon $PREFIX/bin/transmission-daemon.bin
cp ~/transmission-wrapper.sh $PREFIX/bin/transmission-daemon
chmod +x $PREFIX/bin/transmission-daemon

echo "Installing python packages..."
pip install flask requests

echo "Starting sshd so agent can connect..."
sshd
