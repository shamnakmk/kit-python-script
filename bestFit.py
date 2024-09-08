import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
import requests
import json
import urllib.parse
import sys
import statistics
import numpy
import traceback
import time
import math


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
	configFile = '/usr/local/etc/dashcalc.conf'
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
inputDataElementIds = dhis['inputDataElementIds']
outputDataElementIds = dhis['outputDataElementIds']
period = dhis['period']
numberOfPastQuarters = dhis['numberOfPastQuarters']
numberOfFutureQuarters = dhis['numberOfFutureQuarters']
attributeOptions = dhis['attributeOptions']
defaultOption = dhis['defaultOption']
orgUnit = dhis['orgUnit']
allFormsMaleDataElementId = dhis["allFormsMaleDataElementId"]
allFormsFemaleDataElementId = dhis["allFormsFemaleDataElementId"]
allFormsOutputDataElemenIds = dhis["allFormsOutputDataElemenIds"]







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
		# print(api + args) # debug
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

#
            
def get_previous_periods(starting_period, number):
    periodsArray = []
    
    # Parse the input starting period (e.g., '2024Q3')
    year = int(starting_period[:4])
    quarter = int(starting_period[-1])
    # Loop backward to generate periods
    for i in range(number):
        periodsArray.append(f"{year}Q{quarter}")
        quarter -= 1
        if quarter == 0:
            year -= 1
            quarter = 4  # Reset to previous year's Q4
    
    return periodsArray

# Get periods dynamically based on the starting period from the config

def get_future_periods(starting_period, number):
    futurePeriodsArray = []
    
    # Parse the input starting period (e.g., '2024Q3')
    year = int(starting_period[:4])
    quarter = int(starting_period[-1])
    # Loop backward to generate periods
    for i in range(number):
        quarter += 1
        if quarter == 5:
            year += 1
            quarter = 1 
        futurePeriodsArray.append(f"{year}Q{quarter}") # Reset to previous year's Q4
    
    return futurePeriodsArray


pastPeriods = get_previous_periods(period,numberOfPastQuarters)
pastPeriods.sort()
pastAndFuturePeriods = pastPeriods + get_future_periods(period,numberOfFutureQuarters)

pastAndFuturePeriods.sort()
print(pastPeriods)
print(pastAndFuturePeriods)
periodString = ''
for i in range (len(pastPeriods)):
    periodString += '&period='+pastPeriods[i]

quarter_numbers=[]
for q in range(1,numberOfPastQuarters+1):
    quarter_numbers.append(q)


#create a function that accepts a inputDataElementId, periodsString, orgUnit and AttributeOption Uid
#Returns 12 data values for that inputDataElementId

def getDataValues(inputDataElementId,orgUnitId,periodsString,attributeOptionUid):
    print("Fetching data values for data element:"+inputDataElementId+",attributeOption:"+attributeOptionUid)
    dataValuesResult = d2get('dataValueSets.json?dataElement='+inputDataElementId+periodsString+'&orgUnit='+orgUnitId+'&attributeOptionCombo='+attributeOptionUid,'dataValues')

    #Sort Data Values in ascending order of quarters
    # Sort based on the 'age' key
    dataValuesSorted = sorted(dataValuesResult, key=itemgetter('period'))

    values=[]
    for d in range(len(dataValuesSorted)):
        values.append(int(dataValuesSorted[d]['value']))

    print("Sorted Data Values Fetched:", str(values))
    return values

def getAllFormDataValues(maleInputDataElementId,femaleInputDataElementId,attributeOption):
    
    male = maleInputDataElementId
    female= femaleInputDataElementId

    
        

    maleDataValues = getDataValues(male,orgUnit,periodString,attributeOption)
    femaleDataValues = getDataValues(female,orgUnit,periodString,attributeOption)

    print("Male DataElement Values:",str(maleDataValues))
    print("Female DataElement Values:", str(femaleDataValues))

    allFormsTotal = []

    for l in range(len(maleDataValues)):
        allFormsTotal.append(maleDataValues[l]+femaleDataValues[l])

    print(allFormsTotal)

    return allFormsTotal

def calculatePredictions(xValues,yValues,numberOfPredictions):
    x = np.array(xValues)
    y = np.array(yValues)

        #find line of best fit
    a, b = np.polyfit(x, y, 1)
    predictions =[]
    for p in range (1,numberOfPredictions+1):
        y=(a*p+b)
        predictions.append(round(y))
    return predictions
      


for k in range (len(attributeOptions)):
    
    allFormsTotal = getAllFormDataValues(allFormsMaleDataElementId,allFormsFemaleDataElementId,attributeOptions[k])
    predictions = calculatePredictions(quarter_numbers,allFormsTotal,numberOfPastQuarters+numberOfFutureQuarters)
    
    allFormsDataValues= []
    for m in range(16):
        dataValue = { "categoryOptionCombo": defaultOption,
            "attributeOptionCombo": defaultOption,
            "dataElement":allFormsOutputDataElemenIds[k],
            "period":pastAndFuturePeriods[m],
            "orgUnit": orgUnit,
            "value": str(predictions[m])
        }
    
        allFormsDataValues.append(dataValue)
    print(" all from data value payload:",str(allFormsDataValues))




    allFormsPayload= {'dataValues': allFormsDataValues}

    print('Pushing dataValues to dataElement=',str(allFormsOutputDataElemenIds[k]),'with Payload=',str(allFormsPayload))
    status = d2post("dataValueSets.json",allFormsPayload)
    print(status)
    





for i in range(len(inputDataElementIds)):
    
    inputDataElement = inputDataElementIds[i]
    
    
    for j in range(len(attributeOptions)):
       
        outputDataElement = outputDataElementIds[i][j]
        attributeOption = attributeOptions[j]
        values = getDataValues(inputDataElement,orgUnit,periodString,attributeOption)
        predictions = calculatePredictions(quarter_numbers,values,numberOfPastQuarters+numberOfFutureQuarters)

       
        

       
        
        print("Predictions for input:"+inputDataElement+",attributeOption:"+attributeOption+", is: "+ str(predictions))

        dataValues= []
        for o in range(16):
            dataValue = { "categoryOptionCombo": defaultOption,
                "attributeOptionCombo": defaultOption,
                "dataElement":outputDataElement,
                 "period":pastAndFuturePeriods[o],
                 "orgUnit": orgUnit,
                 "value": str(predictions[o])
            }
    
            dataValues.append(dataValue)
    



        payload= {}
        payload['dataValues'] = dataValues
        print('Pushing dataValues to dataElement='+outputDataElement+ ' with Payload='+str(payload))
        status = d2post("dataValueSets.json",payload)
        print(status)


