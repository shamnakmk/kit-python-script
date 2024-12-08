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
allFormsMaleDataElementIds = dhis["allFormsMaleDataElementIds"]
allFormsFemaleDataElementIds = dhis["allFormsFemaleDataElementIds"]
allFormsOutputDataElemenIds = dhis["allFormsOutputDataElemenIds"]
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

skippedAllFormsPredictions = []
skippedNRPredictions = []

pushedAllFormsPredictions = []
pushedNRPredictions = []
      
for p in range (len(orgUnits)):
    orgUnit = orgUnits[p]
    #print("fetched orgUnit is " + orgUnit)

    for k in range(len(allFormsOutputDataElemenIds)):
    
        #maleDataValues = getDataValues(allFormsMaleDataElementIds[k],orgUnit,periodString)
        #femaleDataValues = getDataValues(allFormsFemaleDataElementIds[k],orgUnit,periodString)
        #print("male data values is:" + str(maleDataValues) )
        #print("female data values is:" + str(femaleDataValues) )
        pulmonaryBNRDataValuesResult = getDataValuesResult( pulmonaryBNR[k],orgUnit,periodString)
        if len(pulmonaryBNRDataValuesResult)!= numberOfPastQuarters:
            print("Number of pulmonaryBNRDataValues is not equals number of pastPeriods. Skipping all forms prediction")
            skippedAllFormsPredictions.append(orgUnit+"-pulmonaryBNRDataValues")
            continue

        pulmonaryBOtherDataValuesResult = getDataValuesResult( pulmonaryBOther[k],orgUnit,periodString)
        if len(pulmonaryBOtherDataValuesResult)!= numberOfPastQuarters:
            print("Number of pulmonaryBOtherDataValues is not equals number of pastPeriods. Skipping all forms prediction")
            skippedAllFormsPredictions.append(orgUnit+"-pulmonaryBOtherDataValues")
            continue


        pulmonaryCDNRDataValuesResult = getDataValuesResult( pulmonaryCDNR[k],orgUnit,periodString)
        if len(pulmonaryCDNRDataValuesResult)!= numberOfPastQuarters:
            print("Number of pulmonaryCDNRDataValues is not equals number of pastPeriods. Skipping all forms prediction")
            skippedAllFormsPredictions.append(orgUnit+"-pulmonaryCDNRDataValues")
            continue


        pulmonaryCDOtherDataValuesResult = getDataValuesResult( pulmonaryCDOther[k],orgUnit,periodString)
        if len(pulmonaryCDOtherDataValuesResult)!= numberOfPastQuarters:
            print("Number of pulmonaryCDOtherDataValues is not equals number of pastPeriods. Skipping all forms prediction")
            skippedAllFormsPredictions.append(orgUnit+"-pulmonaryCDOtherDataValues")
            continue


        extraPulmonaryNRDataValuesResult = getDataValuesResult( extraPulmonaryNR[k],orgUnit,periodString)
        if len(extraPulmonaryNRDataValuesResult)!= numberOfPastQuarters:
            print("Number of extraPulmonaryNRDataValues is not equals number of pastPeriods. Skipping all forms prediction")
            skippedAllFormsPredictions.append(orgUnit+"-extraPulmonaryNRDataValues")
            continue


        extraPulmonaryOtherDataValuesResult = getDataValuesResult( extraPulmonaryOther[k],orgUnit,periodString)
        if len(extraPulmonaryOtherDataValuesResult)!= numberOfPastQuarters:
            print("Number of extraPulmonaryOtherDataValues is not equals number of pastPeriods. Skipping all forms prediction")
            skippedAllFormsPredictions.append(orgUnit+"-extraPulmonaryOtherDataValues")
            continue

        pulmonaryBNRDataValues = sortAndNumerifyDataValues(pulmonaryBNRDataValuesResult)
        pulmonaryBOtherDataValues = sortAndNumerifyDataValues(pulmonaryBOtherDataValuesResult)
        pulmonaryCDNRDataValues = sortAndNumerifyDataValues(pulmonaryCDNRDataValuesResult)
        pulmonaryCDOtherDataValues = sortAndNumerifyDataValues(pulmonaryCDOtherDataValuesResult)
        extraPulmonaryNRDataValues = sortAndNumerifyDataValues(extraPulmonaryNRDataValuesResult)
        extraPulmonaryOtherDataValues = sortAndNumerifyDataValues(extraPulmonaryOtherDataValuesResult)
        

        allFormsTotal = []
        for l in range(len(pulmonaryBNRDataValues)):
            allFormsTotal.append(pulmonaryBNRDataValues[l]+pulmonaryBOtherDataValues[l]+pulmonaryCDNRDataValues[l]+pulmonaryCDOtherDataValues[l]+extraPulmonaryNRDataValues[l]+extraPulmonaryOtherDataValues[l])
        
        predictions = calculatePredictions(quarter_numbers,allFormsTotal,numberOfPastQuarters+numberOfFutureQuarters)
        # print("AllForms Predictions:"+str(predictions))

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



        allFormsPayload= {'dataValues': allFormsDataValues}

        # print('Pushing All Forms dataValues to dataElement=',str(allFormsOutputDataElemenIds[k]),'with Payload=',str(allFormsPayload))
        status = d2post("dataValueSets.json",allFormsPayload)
        print(status)
        pushedAllFormsPredictions.append(orgUnit)
    



for q in range (len(orgUnits)):
    orgUnit = orgUnits[q]
    # print("fetched orgUnit is" + orgUnit)

    for i in range(len(inputDataElementIds)):
        
        inputDataElement = inputDataElementIds[i]
        outputDataElement = outputDataElementIds[i]
        
        
        dataValuesResult = getDataValuesResult(inputDataElement,orgUnit,periodString)

        if len(dataValuesResult)!=numberOfPastQuarters:
            print("Past dataValues of " +str(inputDataElement)+ " is not matching the number of past periods")
            skippedNRPredictions.append(orgUnit+"-"+str(inputDataElement))
            continue

        values = sortAndNumerifyDataValues(dataValuesResult)
        predictions = calculatePredictions(quarter_numbers,values,numberOfPastQuarters+numberOfFutureQuarters)
       #  print("Predictions:"+str(predictions))

        
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
        # print('Pushing dataValues to dataElement='+outputDataElement+ ' with Payload='+str(payload))
        status = d2post("dataValueSets.json",payload)
        print(status)
        pushedNRPredictions.append(orgUnit+"-"+outputDataElement)


print("Predictions Run Summary")
print("Total AllForms predictions pushed:"+str(len(pushedAllFormsPredictions)))
print("Total NR predictions pushed:"+str(len(pushedNRPredictions)))
print("Total AllForms predictions skipped due to missing data:"+str(len(skippedAllFormsPredictions)))
print("Total NR predictions skipped due to missing data:"+str(len(skippedNRPredictions)))

print("Skip Summary")
print("All Forms Predictions Skipped (OrgUnitId-DataElement)")
print(skippedAllFormsPredictions)
print("NR Predictions Skipped (OrgUnitId-DataElement)")
print(skippedNRPredictions)


