#!/bin/sh
sudo /bin/launchctl unload /Library/LaunchDaemons/com.testplant.iosinst.plist
sudo rm /Library/LaunchDaemons/com.testplant.iosinst.plist
cd
sudo rm /var/log/iosinstService.log
sudo rm -rf /Library/iosinstService
