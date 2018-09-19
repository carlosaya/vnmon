import boto3
import subprocess
import re
from datetime import *
import dateutil.tz

offset = dateutil.tz.tzoffset(None, 10*60*60)
offsetLastHour = dateutil.tz.tzoffset(None, 10*60*60 - 3600)

now = datetime.now(offset)
today = now.strftime('%m/%d/%y')
yesterday = (now - timedelta(1)).strftime('%m/%d/%y')

month = str(now.month).zfill(2)
day = str(now.day).zfill(2)
year = now.year

currentHour = str(now.hour).zfill(2)
lastHour = str(datetime.now(offsetLastHour).hour).zfill(2)

command = 'vnstat -d'
process = subprocess.Popen(command.split(), stdout=subprocess.PIPE)
output, error = process.communicate()

dates = re.findall('([0-9]{2}\/[0-9]{2}\/[0-9]{2})', output)

rxValues = []
txValues = []
toValues = []
total = 0

ddb = boto3.client('dynamodb')
ddbKeys = []

# Get existing data from dynamo
for date in dates:
    ddbKeys.append({'date': {'S': date} })

ddbItems = ddb.batch_get_item(
    RequestItems = {
        'vnmon-daily': {
            'Keys': ddbKeys
        }
    })

# Get data from vnstat
for date in dates:
    data = re.findall("%s.*" % date, output)
    line = re.findall("%s.*" % date, output)
    data = re.findall("\d*\.\d{2} .iB", line[0])    
    txUnit = re.search(".iB", data[1]).group(0)
    toUnit = re.search(".iB", data[2]).group(0)
    txVal = data[1].split(' ')[0]
    toVal = data[2].split(' ')[0]
    if txUnit == "MiB":
        txVal = float(round(float(txVal)/1024, 3))
    if txUnit == "KiB":
        txVal = float(round(float(txVal)/1048576, 3))
    if toUnit == "MiB":
        toVal = float(round(float(toVal)/1024, 3))
    if toUnit == "KiB":
        toVal = float(round(float(toVal)/1048576, 3))
    rxVal = float(round(float(toVal) - float(txVal), 3))
    rxValues.append(rxVal)
    txValues.append(txVal)
    toValues.append(toVal)
    print("{0}: rx={1}   tx={2}   tot={3}".format(date, rxVal, txVal, toVal))
    # Check against dynamo
    match = False
    for item in ddbItems['Responses']['vnmon-daily']:
        if item['date']['S'] == date:
            match = True
    if not match or date == today:
        ddb.update_item(
            TableName = 'vnmon-daily',
            Key = {'date': {'S':date}},
            UpdateExpression = 'SET #tx = :txval, #rx = :rxval, #to = :toval',
            ExpressionAttributeNames = {
		"#to": "to",
		"#tx": "tx",
		"#rx": "rx"
            },
            ExpressionAttributeValues = {
                ":txval": {'N': str(txVal)},
                ":rxval": {'N': str(rxVal)},
                ":toval": {'N': str(toVal)},
            }
        )

# Update 24h stats
command = 'vnstat -h | grep "^[0-9][0-9].*"'
process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
output, error = process.communicate()
lines = output.split('\n')

hourlyData1 = []
hourlyData2 = []
hourlyData3 = []

for line in lines:
    if line == '':
        continue
    split = line.split()
    hourlyData1.append({"hour": split[0], "rx": split[1], "tx": split[2]})
    hourlyData2.append({"hour": split[3], "rx": split[4], "tx": split[5]})
    hourlyData3.append({"hour": split[6], "rx": split[7], "tx": split[8]})

hourlyData = hourlyData1 + hourlyData2 + hourlyData3
for entry in hourlyData:
    date = None
    if entry['hour'] <= currentHour:
        date = today
    else:
        date = yesterday

    if date:
        ddb.update_item(
            TableName = 'vnmon-daily',
            Key = {'date': {'S':date}},
            UpdateExpression = 'SET #tx = :txval, #rx = :rxval',
            ExpressionAttributeNames = {
                "#tx": "{0}tx".format(str(entry['hour'])),
                "#rx": "{0}rx".format(str(entry['hour']))
            },
            ExpressionAttributeValues = {
                ":txval": {'N': entry['tx']},
                ":rxval": {'N': entry['rx']}
            }
        )
