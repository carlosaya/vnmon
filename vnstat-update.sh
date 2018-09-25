#/bin/bash
cd /config/scripts/vnmon/

git pull

python ./vnstat-update.py

mkdir vnstat-data	
currenttime=$(date +%H:%M)	
if [[ "$currenttime" = "06:20" ]]; then	
  cp -Rf /var/log/vnstat ./vnstat-data
  git add .
  git commit -m 'daily vnstat backup'
  git push
fi


