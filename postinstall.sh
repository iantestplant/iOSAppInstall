#!/bin/sh
#sudo /Library/iosinstService/setup.sh
cd /Library/iosinstService
sudo python virtualenv.py venv
sudo venv/bin/pip install -r requirements.txt

sudo /bin/launchctl load /Library/LaunchDaemons/com.testplant.iosinst.plist
