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
	configFile = '/usr/local/etc/bestFit.conf'
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
defaultOption = dhis['defaultOption']
orgUnits = dhis['orgUnits']
allFormsOutputDataElementId = dhis["allFormsOutputDataElementId"]
pulmonaryBNR = dhis["pulmonaryBNR"]
pulmonaryBOther = dhis["pulmonaryBOther"]
pulmonaryCDNR = dhis["pulmonaryCDNR"]
pulmonaryCDOther = dhis["pulmonaryCDOther"]
extraPulmonaryNR = dhis["extraPulmonaryNR"]
extraPulmonaryOther = dhis["extraPulmonaryOther"]

                    


#Validating config

if len(inputDataElementIds) != len(outputDataElementIds):
      print("Number of input dataElements does not match number of output data elements. Please check conf file")
      sys.exit()


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


#organisationUnit = d2get('organisationUnits','organisationUnits')
#print(organisationUnit)
           
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

#create a function that accepts a inputDataElementId, periodsString, orgUnit and AttributeOption Uid
#Returns 12 data values for that inputDataElementId

def getDataValues(inputDataElementId,orgUnitId,periodsString):
    #print("Fetching data values for data element:"+inputDataElementId)
    dataValuesResult = d2get('dataValueSets.json?dataElement='+inputDataElementId+periodsString+'&orgUnit='+orgUnitId+"&attributeOptionCombo="+defaultOption,'dataValues')

    #Sort Data Values in ascending order of quarters
    # Sort based on the 'age' key
    dataValuesSorted = sorted(dataValuesResult, key=itemgetter('period'))

    values=[]
    for d in range(len(dataValuesSorted)):
        values.append(int(dataValuesSorted[d]['value']))


    #print("Sorted Data Values Fetched:", str(values))
    return values

def getDataValuesResult(inputDataElementId,orgUnitId,periodsString):
    #print("Fetching data values for data element:"+inputDataElementId)
    return d2get('dataValueSets.json?dataElement='+inputDataElementId+periodsString+'&orgUnit='+orgUnitId+"&attributeOptionCombo="+defaultOption,'dataValues')

def getDataValuesForDataElementsInOrgUnits(inputDataElementIds,orgUnitIds,periodsString, fillZeroes, requiredPeriods):
    requiredPeriods.sort()
    dataElementQueryParam = ''
    orgUnitQueryParam=''
    for i in range (len(inputDataElementIds)):
        dataElementQueryParam += '&dataElement='+inputDataElementIds[i]
    for j in range (len(orgUnitIds)):
        orgUnitQueryParam += '&orgUnit='+orgUnitIds[j]

    url = 'dataValueSets.json?attributeOptionCombo='+defaultOption+dataElementQueryParam+periodsString+orgUnitQueryParam

    allDataValues =  d2get(url,'dataValues')

    # Initialize the dataValueMap
    dataValueMap = {}

    for dataValue in allDataValues:
        orgUnit = dataValue["orgUnit"]
        dataElement = dataValue["dataElement"]
        period = dataValue["period"]
        value = dataValue["value"]

        # Initialize the orgUnit entry if it does not exist
        if orgUnit not in dataValueMap:
            dataValueMap[orgUnit] = {}

        # Initialize the dataElement entry if it does not exist
        if dataElement not in dataValueMap[orgUnit]:
            dataValueMap[orgUnit][dataElement] = {
                "periodValues": {},  # Period-value mapping
                "stringDataValues": [],
                "dataValues": []  # Values ordered by requiredPeriods
            }


        # Add or update the period-value mapping
        dataValueMap[orgUnit][dataElement]["periodValues"][period] = value

    
    # Fill missing periods with zeroes if fillZeroes is true
    for orgUnit, dataElements in dataValueMap.items():
        for dataElement, dataElementData in dataElements.items():
            periodValues = dataElementData["periodValues"]

            # Fill missing periods with zeroes
            if fillZeroes:
                for requiredPeriod in requiredPeriods:
                    if requiredPeriod not in periodValues:
                        periodValues[requiredPeriod] = "0"

            # Add the dataValues array ordered by requiredPeriods
            dataElementData["stringDataValues"] = [
                periodValues.get(period, "0") for period in requiredPeriods
            ]

            # Code to fill dataValues
            dataElementData["dataValues"] = [
                    int(periodValues.get(period)) if periodValues.get(period) is not None and periodValues.get(period).isdigit() else None
                    for period in requiredPeriods
            ]
            
            # Remove None values (if needed)
            dataElementData["dataValues"] = [value for value in dataElementData["dataValues"] if value is not None]

    return dataValueMap



def sortAndNumerifyDataValues(dataValuesResult):
    #Sort Data Values in ascending order of quarters
    # Sort based on the 'age' key
    dataValuesSorted = sorted(dataValuesResult, key=itemgetter('period'))

    values=[]
    for d in range(len(dataValuesSorted)):
        if dataValuesSorted[d]['value'] is not None and str(dataValuesSorted[d]['value']).isdigit():
            values.append(int(dataValuesSorted[d]['value']))
        else:
            print('Got a non numeric data value=',dataValuesSorted[d]['value'])

    #print("Sorted Data Values Fetched:", str(values))
    return values

def getDataValuesWithZeroes(inputDataElementId,orgUnitId,periodsString):
    #print("Fetching data values for data element:"+inputDataElementId)
    dataValuesResult = d2get('dataValueSets.json?dataElement='+inputDataElementId+periodsString+'&orgUnit='+orgUnitId+"&attributeOptionCombo="+defaultOption,'dataValues')
    periodDataValues= {}
    for s in range (len(dataValuesResult)):
         periodDataValues[dataValuesResult[s]["period"]] = int(dataValuesResult[s]["value"])


    values=[]

    for p in range(len(pastPeriods)):
        period = pastPeriods[p]
        if period in periodDataValues:
             values.append(periodDataValues[period])
        else:
             values.append(0)
             
         
    #print("Sorted Data Values Fetched:", str(values))
    return values


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

pastPeriods = get_previous_periods(period,numberOfPastQuarters)
pastPeriods.sort()
pastAndFuturePeriods = pastPeriods + get_future_periods(period,numberOfFutureQuarters)

pastAndFuturePeriods.sort()
#print(pastPeriods)
#print(pastAndFuturePeriods)
periodString = ''
for i in range (len(pastPeriods)):
    periodString += '&period='+pastPeriods[i]

quarter_numbers=[]
for q in range(1,numberOfPastQuarters+1):
    quarter_numbers.append(q)

skippedAllFormsPredictions = []
skippedNRPredictions = []

pushedAllFormsPredictions = []
pushedNRPredictions = []
coveredOrgUnits = 0;
skippedOrgUnits = 0;


batch_size = 10
# Loop through the orgUnitIds in batches of 10
for i in range(0, len(orgUnits), batch_size):
    orgUnitsBatched = orgUnits[i:i + batch_size]  # Slice the batch

    dataValueResultMap = getDataValuesForDataElementsInOrgUnits(inputDataElementIds+[pulmonaryBOther,pulmonaryCDOther,extraPulmonaryOther],orgUnitsBatched,periodString,True,pastPeriods)

    print(dataValueResultMap)
    predictedAllFormsDataValues = []
    predictedNRDataValues= []

    for p in range (len(orgUnitsBatched)):
        orgUnit = orgUnitsBatched[p]
        #print("fetched orgUnit is " + orgUnit)
        if dataValueResultMap.get(orgUnit) is None:
            skippedOrgUnits = skippedOrgUnits+1
            continue

        for i in range(len(inputDataElementIds)):
        
            inputDataElement = inputDataElementIds[i]
            outputDataElement = outputDataElementIds[i]
        
            if dataValueResultMap[orgUnit].get(inputDataElement) is None:
                skippedOrgUnits = skippedOrgUnits+1
                continue

            dataValuesForDE = dataValueResultMap[orgUnit][inputDataElement]["dataValues"]

            if len(dataValuesForDE)!=numberOfPastQuarters:
                print("Past dataValues of " +str(inputDataElement)+ " is not matching the number of past periods")
                skippedNRPredictions.append(orgUnit+"-"+str(inputDataElement))
                continue

            predictions = calculatePredictions(quarter_numbers,dataValuesForDE,numberOfPastQuarters+numberOfFutureQuarters)
            pushedNRPredictions.append(orgUnit+"-"+outputDataElement)
            print(inputDataElement)
            print(outputDataElement)
            print(dataValuesForDE)
            print(predictions)
            for o in range(len(pastAndFuturePeriods)):
                dataValue = { "categoryOptionCombo": defaultOption,
                "attributeOptionCombo": defaultOption,
                "dataElement":outputDataElement,
                "period":pastAndFuturePeriods[o],
                "orgUnit": orgUnit,
                "value": str(predictions[o])
                }
    
                predictedNRDataValues.append(dataValue)

        
        if dataValueResultMap[orgUnit].get(pulmonaryBNR) is None or dataValueResultMap[orgUnit].get(pulmonaryBOther) is None or dataValueResultMap[orgUnit].get(pulmonaryCDNR) is None or dataValueResultMap[orgUnit].get(pulmonaryCDOther) is None or dataValueResultMap[orgUnit].get(extraPulmonaryNR) is None or dataValueResultMap[orgUnit].get(extraPulmonaryOther) is None:
            print("Datavalue missing for one of allForms calculation. Skipping all forms prediction for orgUnit:"+orgUnit)
            skippedAllFormsPredictions.append(orgUnit)
            continue
        
        pulmonaryBNRDataValues = dataValueResultMap[orgUnit][pulmonaryBNR]["dataValues"]
        pulmonaryBOtherDataValues = dataValueResultMap[orgUnit][pulmonaryBOther]["dataValues"]
        pulmonaryCDNRDataValues  = dataValueResultMap[orgUnit][pulmonaryCDNR]["dataValues"]
        pulmonaryCDOtherDataValues = dataValueResultMap[orgUnit][pulmonaryCDOther]["dataValues"]
        extraPulmonaryNRDataValues = dataValueResultMap[orgUnit][extraPulmonaryNR]["dataValues"]
        extraPulmonaryOtherDataValues = dataValueResultMap[orgUnit][extraPulmonaryOther]["dataValues"]
        if len(pulmonaryBNRDataValues)!= numberOfPastQuarters or len(pulmonaryBOtherDataValues)!= numberOfPastQuarters or len(pulmonaryCDNRDataValues)!= numberOfPastQuarters or len(pulmonaryCDOtherDataValues)!= numberOfPastQuarters or len(extraPulmonaryNRDataValues)!= numberOfPastQuarters or len(extraPulmonaryOtherDataValues)!= numberOfPastQuarters :
            print("Number of dataValues is not equals number of pastPeriods. Skipping all forms prediction for orgUnit:"+orgUnit)
            skippedAllFormsPredictions.append(orgUnit)
            continue
        

        allFormsTotal = []
        for l in range(len(pulmonaryBNRDataValues)):
            allFormsTotal.append(pulmonaryBNRDataValues[l]+pulmonaryBOtherDataValues[l]+pulmonaryCDNRDataValues[l]+pulmonaryCDOtherDataValues[l]+extraPulmonaryNRDataValues[l]+extraPulmonaryOtherDataValues[l])
        
        predictions = calculatePredictions(quarter_numbers,allFormsTotal,numberOfPastQuarters+numberOfFutureQuarters)
        print("All Forms values", allFormsTotal)
        print("AllForms Predictions:"+str(predictions))

        for m in range(len(pastAndFuturePeriods)):
            dataValue = { "categoryOptionCombo": defaultOption,
                "attributeOptionCombo": defaultOption,
                "dataElement":allFormsOutputDataElementId,
                "period":pastAndFuturePeriods[m],
                "orgUnit": orgUnit,
                "value": str(predictions[m])
            }
            predictedAllFormsDataValues.append(dataValue)

        pushedAllFormsPredictions.append(orgUnit)

    payload= {}
    payload['dataValues'] = predictedNRDataValues + predictedAllFormsDataValues
    print('Pushing dataValues with Payload='+str(payload))
        
    status = d2post("dataValueSets.json",payload)
    print(status)
    coveredOrgUnits = coveredOrgUnits+len(orgUnitsBatched);
    print("Completed no. of orgunits="+str(coveredOrgUnits))



print("**********************")
print("Predictions Run Summary")
print("Total AllForms predictions pushed:"+str(len(pushedAllFormsPredictions)))
print("Total NR predictions pushed:"+str(len(pushedNRPredictions)))
print("Total AllForms predictions skipped due to missing data:"+str(len(skippedAllFormsPredictions)))
print("Total NR predictions skipped due to missing data:"+str(len(skippedNRPredictions)))
print("**********************")
print("Skip Summary")
print("All Forms Predictions Skipped For OrgUnits")
print(skippedAllFormsPredictions)
print("NR Predictions Skipped for OrgUnits")
print(skippedNRPredictions)
print("**********************")
print("Push Summary")
print("All Forms Predictions Pushed for OrgUnits")
print(pushedAllFormsPredictions)
print("NR Predictions Pushed for OrgUnits")
print(pushedNRPredictions)


