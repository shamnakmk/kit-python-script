import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
import requests
import json
import sys
import time
import sys


startTime = datetime.datetime.now()
#
# Convert month string to a sequential number, e.g.:
# '201912' (December 2019) -> 24239
# '202001' (January 2020) -> 24240
#
def toNumber(month):
	return int(month[:4])*12 + int(month[4:])-1

#
# Convert sequential number to a month string
#
def toMonth(monthNumber):
	return str(monthNumber//12) + str(101+monthNumber%12)[1:]

#
# Find today and last month
#
today = datetime.date.today()
thisMonth = today.strftime('%Y%m')
thisMonthNumber = toNumber(thisMonth)
#
# load the configuration
#
if len(sys.argv) < 2:
	configFile = '/usr/local/etc/orgUnits.conf'
else:
    configFile = sys.argv[1]


try:
	configContents = open(configFile).read()
except Exception as e:
	print("Can't read configuration file:", e)
	sys.exit(1)

try:
	config = json.loads(configContents)
except Exception as e:
	print('Configuration file format error: in "' + configFile + '":', e)
	sys.exit(1)

dhis = config['dhis']
baseUrl = dhis['baseurl']
api = baseUrl + '/api/'
credentials = (dhis['username'], dhis['password'])
orgUnitNames = dhis['orgUnitNames']
orgUnitPairs = dhis['orgUnitPairs']
projectOrgUnitId = dhis['projectOrgUnitId']


try:
	response = requests.get(api + 'me', auth=credentials)
	if response.status_code != 200:
		print('Error connecting to DHIS 2 system at "' + baseUrl + '" with username "' + dhis['username'] + '":', response)
		sys.exit(1)
except Exception as e:
	print('Cannot connect to DHIS 2 system at "' + baseUrl + '" with username "' + dhis['username'] + '":', e)
	sys.exit(1)


#
# Handy functions for accessing dhis 2
#
def d2get(args, objects):
	retry = 0 # Sometimes gets a [502] error, waiting and retrying helps
	while True:
		print(api + args) # debug
		response = requests.get(api + args.replace('[','%5B').replace(']','%5D'), auth=credentials)
		try:
			# print(api + args + ' --', len(response.json()[objects]))
			return response.json()[objects]
		except:
			retry = retry + 1
			if retry > 3:
				print( 'Tried GET', api + args, '\n' + 'Unexpected server response:', response.text )
				raise
			time.sleep(2)

def d2post(args, data):
	return requests.post(api + args, json=data, auth=credentials)


for o in range(len(orgUnitNames)):
    orgUnit = { "name": orgUnitNames[o],
                "shortName": orgUnitNames[o],
                "openingDate": "1995-01-01T00:00:00.000"
            }
        
    print('Adding orgunit with  Payload=',str(orgUnit))
    status = d2post("organisationUnits.json",orgUnit)
    print(status)
    
orgUnitIdMap = {}

if projectOrgUnitId is None:
	sys.exit(0)
    
for i in range(len(orgUnitPairs)):
	parentId = None
	ouPair = orgUnitPairs[i]
	if ouPair[0] in orgUnitIdMap:
		parentId = orgUnitIdMap[ouPair[0]]
	else:
		parentOu = { "name": ouPair[0],
                "shortName": ouPair[0],
                "openingDate": "1995-01-01T00:00:00.000",
		"parent" : {"id": projectOrgUnitId}
            }
		print('Adding parent orgunit =',str(ouPair[0]))
		status = d2post("organisationUnits.json",parentOu)
		print(status)
		parentId = status.json()["response"]["uid"]
		orgUnitIdMap[ouPair[0]] = parentId

	childOu = { "name": ouPair[1],
                "shortName": ouPair[1],
                "openingDate": "1995-01-01T00:00:00.000",
				"parent" : {"id": parentId}
            }
	
	print('Adding child orgunit =',str(ouPair[1]), " under parent=",str(ouPair[0]))
	status = d2post("organisationUnits.json",childOu)
	print(status)
	

	


    


