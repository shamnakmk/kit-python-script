import numpy as np
import requests
import json
import sys
import time
import sys



#
# Load the Config File. 
# This script optionally accepts a argument, which will be considered as the conf file.
# If no argument provided, default location of '/usr/local/etc/bestFit.conf' is searched.
# If no config file available or unable to read, script will exit.
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


# Load various configs in conf file to variables.
dhis = config['dhis']
baseUrl = dhis['baseurl']
api = baseUrl + '/api/'
credentials = (dhis['username'], dhis['password'])
inputDataElementIds = dhis['inputDataElementIds']
outputDataElementIds = dhis['outputDataElementIds']
numberOfPastQuarters = dhis['numberOfPastQuarters']
numberOfFutureQuarters = dhis['numberOfFutureQuarters']
defaultOption = dhis['defaultOption']
dataSetIds = dhis['dataSetIds']
allFormsOutputDataElementId = dhis["allFormsOutputDataElementId"]
pulmonaryBNR = dhis["pulmonaryBNR"]
pulmonaryBOther = dhis["pulmonaryBOther"]
pulmonaryCDNR = dhis["pulmonaryCDNR"]
pulmonaryCDOther = dhis["pulmonaryCDOther"]
extraPulmonaryNR = dhis["extraPulmonaryNR"]
extraPulmonaryOther = dhis["extraPulmonaryOther"]
projects = dhis["projects"]
   


#Validate Configs. If any validaion fails, script will exit with failure.

if len(inputDataElementIds) != len(outputDataElementIds):
      print("Number of input dataElements does not match number of output data elements. Please check conf file")
      sys.exit(1)

try:
	response = requests.get(api + 'me', auth=credentials)
	if response.status_code != 200:
		print('Error connecting to DHIS 2 system at "' + baseUrl + '" with username "' + dhis['username'] + '":', response)
		sys.exit(1)
except Exception as e:
	print('Cannot connect to DHIS 2 system at "' + baseUrl + '" with username "' + dhis['username'] + '":', e)
	sys.exit(1)


###################### HELPER FUNCTIONS START ################################

#
# Handy function for getting data out of dhis2 with GET API
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

#
# Handy function for putting data into dhis2 with POST API
#
def d2post(args, data):
	return requests.post(api + args, json=data, auth=credentials)


#
# Function to get previous periods in the form of 2024Q1, 2024Q2 and so on
# starting_period : to indicate from which quarter (like 2024Q3) the count down should begin
# number : to indicate how many previous periods has to be generated (including the starting_period)
# returns an array that contains the required number of previous periods.
# example, if starting_period is 2024Q2 and number is 3, then this function returns
# ['2024Q2','2024Q1','2023Q4']
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


#
# Function to get future periods in the form of 2024Q1, 2024Q2 and so on
# starting_period : to indicate from which quarter (like 2024Q3) the count up should begin
# number : to indicate how many future periods has to be generated (excluding starting_period)
# returns an array that contains the required number of future periods.
# example, if starting_period is 2024Q2 and number is 3, then this function returns
# ['2024Q3','2024Q4','2025Q1']
#
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


# Function that fetches dataValues for all the specified dataElementIds,
# for all the specified orgUnitIds, for the specified periodsString. 
# The function can fill Zeroes (0's) as dataValue if any period is missing an dataValue by using the fillZeroes parameter.
# requiredPeriods is an array of period strings, which is used to compare if any dataValue is missing for any of the required periods.
# This function returns an object as below
# 
def getDataValues(dataElementIds,orgUnitIds,periodsString, fillZeroes, requiredPeriods):
    requiredPeriods.sort()
    dataElementQueryParam = ''
    orgUnitQueryParam=''
    for i in range (len(dataElementIds)):
        dataElementQueryParam += '&dataElement='+dataElementIds[i]
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

            # Code to fill dataValues
            dataElementData["dataValues"] = [
                    int(periodValues.get(period)) if periodValues.get(period) is not None and periodValues.get(period).isdigit() else None
                    for period in requiredPeriods
            ]
            
            # Remove None values (if needed)
           # dataElementData["dataValues"] = [value for value in dataElementData["dataValues"] if value is not None]

    return dataValueMap


# This function calulates predictions based on the input provided.
# xValues is an array of numbers that represent the x coordinate values in the chart for best fit line
# xValues in this case is simply the values from 1 to 12 (depending on number of baseline quarters)
# yValues is an array of numbers that represent the corresponding y coordinate value
# yValues in our case is the dataValues corresponding to the baseline period number
# numberOfPredictions is the number of future predictions required in the best fit line.
# Example: if xValues : [1,2,3,4,5,6]
#         and yValues : [8,22,28,42,48,62]
#         and numberOfPredictions: 8
# then this function returns the full predictions as [10, 20, 30, 40, 50, 60, 71, 81] (Best fit line)
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

###################### HELPER FUNCTIONS END ################################

###################### PREDICTION CALCULATION BEGINS #########################

quarter_numbers=[]
for q in range(1,numberOfPastQuarters+1):
    quarter_numbers.append(q)


#Array variables for holding the summary of script run.
skippedAllFormsPredictions = []
skippedNRPredictions = []
pushedAllFormsPredictions = []
pushedNRPredictions = []
coveredOrgUnits = 0;
skippedOrgUnits = 0;


batch_size = 10
# batch_size variable is used to loop through the orgUnitIds in those batches


#Collect all orgUnits that are attached to the dataSetIds
dataSetIdString = ",".join(dataSetIds)

dataSetResults = d2get('dataSets.json?fields=name,organisationUnits&filter=id:in:['+dataSetIdString+']','dataSets')
dataSetOrgUnits = [organisationUnit["id"] for dataSet in dataSetResults for organisationUnit in dataSet["organisationUnits"]]
dataSetOrgUnits_set = set(dataSetOrgUnits)

#Iterating over each project defined in config and calculating predictions one project at a time.
for p in range(0,len(projects)):

    #If baselineEndQuarter not specified in conf for this project, then skip this project and continue to next in loop
    if (projects[p]['baselineEndQuarter'] == ''):
        print('Skipping project: ' + projects[p]['projectName'] + ' due to missing baselineEndQuarter')
        continue

    pastPeriods = get_previous_periods(projects[p]['baselineEndQuarter'],numberOfPastQuarters)
    pastPeriods.sort()

    pastAndFuturePeriods = pastPeriods + get_future_periods(projects[p]['baselineEndQuarter'],numberOfFutureQuarters)
    pastAndFuturePeriods.sort()

    pastPeriodString = ''
    for i in range (len(pastPeriods)):
        pastPeriodString += '&period='+pastPeriods[i]

    print("Fetching orgUnits under project: " + projects[p]['projectName'])
    porgs = d2get('organisationUnits.json?fields=id&filter=path:like:'+projects[p]['projectOrgUnitId']+'&paging=false','organisationUnits')
    
    # Add child orgUnitIds of project that are also attached to the dataSet
    orgUnits = [porg["id"] for porg in porgs if porg["id"] in dataSetOrgUnits_set ]

    print("Calculating predictions for " + str(len(orgUnits)) + " orgUnits that are attached to DataSet in project: " + projects[p]['projectName'])

    for o in range(0, len(orgUnits), batch_size):
        orgUnitsBatched = orgUnits[o:o + batch_size]  # Slice the batch

        dataValueResultMap = getDataValues(inputDataElementIds+[pulmonaryBOther,pulmonaryCDOther,extraPulmonaryOther],orgUnitsBatched,pastPeriodString,True,pastPeriods)
        print(dataValueResultMap)
        predictedAllFormsDataValues = []
        predictedNRDataValues= []

        for b in range (len(orgUnitsBatched)):
            orgUnit = orgUnitsBatched[b]
           
            if dataValueResultMap.get(orgUnit) is None:
                skippedOrgUnits = skippedOrgUnits+1
                continue

            for d in range(len(inputDataElementIds)):
        
                inputDataElement = inputDataElementIds[d]
                outputDataElement = outputDataElementIds[d]
        
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
        #print('Pushing dataValues with Payload='+str(payload))
        
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


