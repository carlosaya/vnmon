#/bin/bash
cd /config/scripts/vnmon/

git pull

python ./vnstat-update.py

mkdir vnstat-data
currenttime=$(date +%H:%M)
if [[ "$currenttime" = "06:20" ]]; then
	cp -Rf /var/log/vnstat ./vnstat-data
fi


jsonDates=$(vnstat -d | grep -Eo "([0-9]{2}\/[0-9]{2}\/[0-9]{2})" | jq -R '[.]' | jq -s -c 'add')

dates=$(vnstat -d | grep -Eo "([0-9]{2}\/[0-9]{2}\/[0-9]{2})")

rxValues=()
txValues=()
toValues=()
total=0

for date in $dates; do
	tx=$(vnstat -d | grep -Eo "$date.*([0-9]*\.[0-9]{2} .iB |)" | cut -d \| -f 2 | xargs)
	to=$(vnstat -d | grep -Eo "$date.*([0-9]*\.[0-9]{2} .iB |)" | cut -d \| -f 3 | xargs)

	toValue=$(echo $to | cut -d ' ' -f 1)
	toUnit=$(echo $to | cut -d ' ' -f 2)

	txValue=$(echo $tx | cut -d ' ' -f 1)
	txUnit=$(echo $tx | cut -d ' ' -f 2)

	if [[ $txUnit = "MiB" ]]; then
		txValue=$(echo "scale=3; $txValue / 1024" | bc | sed 's/^\./0./')
	elif [[ $txUnit = "KiB" ]]; then
		txValue=$(echo "scale=3; $txValue / 1048576" | bc | sed 's/^\./0./')
	elif [[ $txUnit = "GiB" ]]; then
		txValue=$(echo $txValue | sed 's/^\./0./')
	fi

	if [[ $toUnit = "MiB" ]]; then
		toValue=$(echo "scale=3; $toValue / 1024" | bc | sed 's/^\./0./')
	elif [[ $toUnit = "KiB" ]]; then
		toValue=$(echo "scale=3; $toValue / 1048576" | bc | sed 's/^\./0./')
	elif [[ $toUnit = "GiB" ]]; then
		toValue=$(echo $toValue | sed 's/^\./0./')
	fi

	rxValue=$(echo "scale=3; $toValue - $txValue" | bc | sed 's/^\./0./')

	rxValues+=($rxValue)
	txValues+=($txValue)
	toValues+=($toValue)

	echo "$date: rx=$rxValue   tx=$txValue   tot=$toValue"

done

echo "Begin JSON Summary..."
echo $jsonDates

rxArr=$(echo "["$(printf '%s,' "${rxValues[@]}")"]")
txArr=$(echo "["$(printf '%s,' "${txValues[@]}")"]")
toArr=$(echo "["$(printf '%s,' "${toValues[@]}")"]")

rxArr="${rxArr/,]/]}"
txArr="${txArr/,]/]}"
toArr="${toArr/,]/]}"

echo $rxArr
echo $txArr
echo $toArr

echo "{\"lastUpdated\": \"$(date)\", \"dates\": $(echo $jsonDates), \"rx\": $(echo $rxArr), \"tx\": $(echo $txArr), \"to\": $(echo $toArr)}" > /config/scripts/vnmon/data.json

vnstat -h | grep "^[0-9][0-9].*" > /config/scripts/vnmon/hourly.txt

git add .
git commit -m '5m auto-update'
git push

