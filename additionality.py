import numpy as np
import requests
import json
import sys
import time
import sys
from datetime import date



#
# Load the Config File. 
# This script optionally accepts a argument, which will be considered as the conf file.
# If no argument provided, default location of '/usr/local/etc/bestFit.conf' is searched.
# If no config file available or unable to read, script will exit.
#
if len(sys.argv) < 2:
	configFile = '/usr/local/etc/additionality.conf'
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
adjustedAdditionalityOutputDataElementIds = dhis['adjustedAdditionalityOutputDataElementIds']
unadjustedAdditionalityOutputDataElementIds = dhis['unadjustedAdditionalityOutputDataElementIds']
numberOfPastQuartersForAdjustedAdditionality = dhis['numberOfPastQuartersForAdjustedAdditionality']
numberOfFutureQuartersForAdjustedAdditionality = dhis['numberOfFutureQuartersForAdjustedAdditionality']
defaultOption = dhis['defaultOption']
dataSetIds = dhis['dataSetIds']
adjustedAdditionalityAllFormsOutputDataElementId = dhis['adjustedAdditionalityAllFormsOutputDataElementId']
unadjustedAdditionalityAllFormsOutputDataElementId = dhis['unadjustedAdditionalityAllFormsOutputDataElementId']
pulmonaryBNR = dhis["pulmonaryBNR"]
pulmonaryBOther = dhis["pulmonaryBOther"]
pulmonaryCDNR = dhis["pulmonaryCDNR"]
pulmonaryCDOther = dhis["pulmonaryCDOther"]
extraPulmonaryNR = dhis["extraPulmonaryNR"]
extraPulmonaryOther = dhis["extraPulmonaryOther"]
implementationEndPeriod = dhis["implementationEndPeriod"]
clearPeriods = dhis["clearPeriods"]
projects = dhis["projects"]
   

#Validate Configs. If any validaion fails, script will exit with failure.

if len(inputDataElementIds) != len(adjustedAdditionalityAllFormsOutputDataElementId) or len(inputDataElementIds) !=len(unadjustedAdditionalityAllFormsOutputDataElementId):
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

#
# Function to get future periods in the form of 2024Q1, 2024Q2 and so on
# starting_period : to indicate from which quarter (like 2024Q3) the count up should begin
# number : to indicate how many future periods has to be generated (excluding starting_period)
# returns an array that contains the required number of future periods.
# example, if starting_period is 2024Q2 and number is 3, then this function returns
# ['2024Q3','2024Q4','2025Q1']
#
from datetime import date

def get_future_periods_todate(starting_period, end_period="2025Q1"):
    # Split the starting period like "2024Q3"
    start_year = int(starting_period[:4])
    start_quarter = int(starting_period[-1])

    # Split the ending period like "2025Q1"
    end_year = int(end_period[:4])
    end_quarter = int(end_period[-1])

    # List to hold the periods
    periods = []

    # Start from the next quarter
    year = start_year
    quarter = start_quarter + 1

    # Adjust if quarter goes beyond 4
    if quarter > 4:
        quarter = 1
        year += 1

    # Loop until we reach the end period
    while (year < end_year) or (year == end_year and quarter <= end_quarter):
        periods.append(f"{year}Q{quarter}")
        quarter += 1
        if quarter > 4:
            quarter = 1
            year += 1

    return periods


def deleteDataValues(dataElementIds, orgUnitIds ):
    
    if not clearPeriods:
         return
    
    dataElementQueryParam = ''
    orgUnitQueryParam=''
    periodQueryParam = ''
    for i in range (len(dataElementIds)):
        dataElementQueryParam += '&dataElement='+dataElementIds[i]
    for j in range (len(orgUnitIds)):
        orgUnitQueryParam += '&orgUnit='+orgUnitIds[j]
    for k in range (len(clearPeriods)):
        periodQueryParam +='&period='+clearPeriods[k]


   
    url = 'dataValueSets.json?attributeOptionCombo='+defaultOption+dataElementQueryParam+periodQueryParam+orgUnitQueryParam

    dataValuesToClear =  d2get(url,'dataValues')

    if(len(dataValuesToClear) == 0):
         return
    
    print("Clearing " + str(len(dataValuesToClear)) + " dataValues for periods:"+str(clearPeriods))

    payload= {}
    payload['dataValues'] = dataValuesToClear
    status = d2post("dataValueSets.json?importStrategy=DELETE",payload)
    print(status)


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
            dataElementData["dataValues"] = [0 if value is None else value for value in dataElementData["dataValues"]]

    # Ensure all required dataElements exist for each orgUnit
    for orgUnit, dataElements in dataValueMap.items():
        for requiredDataElementId in dataElementIds:
            if requiredDataElementId not in dataElements:
                # Create the missing data element with 12 zeroes
                dataElements[requiredDataElementId] = {
                    "periodValues": {period: "0" for period in requiredPeriods},
                    "dataValues": [0] * len(requiredPeriods)
                }

    print(dataValueMap)
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


def calculateUnadjustedAdditionality(dataValues,implementationPeriods):
    unadjustedAdditionalityValues = []

    baseline_len = len(dataValues) - len(implementationPeriods)
    implementation_start_index = baseline_len

    for i in range(len(implementationPeriods)):
        implementation_period_number = i + 1

        baseline_sum = sum(dataValues[0 : implementation_period_number])
        implementation_sum = sum(dataValues[implementation_start_index : implementation_start_index + implementation_period_number])

        if implementation_period_number > baseline_len:
            adjustment_factor = implementation_period_number / baseline_len
        else:
            adjustment_factor = 1.0

        adjusted_baseline = baseline_sum * adjustment_factor
        additionality = implementation_sum - adjusted_baseline

        unadjustedAdditionalityValues.append(additionality)

    return unadjustedAdditionalityValues

###################### HELPER FUNCTIONS END ################################

###################### PREDICTION CALCULATION BEGINS #########################

quarter_numbers=[]
for q in range(1,numberOfPastQuartersForAdjustedAdditionality+1):
    quarter_numbers.append(q)

#Array variables for holding the summary of script run.
skippedUnadjustedAllForms = []
skippedUnadjustedNR = []
pushedUnadjustedAllForms = []
pushedUnadjustedNR = []
skippedAdjustedAllFormsPredictions = []
skippedAdjustedNRPredictions = []
pushedAdjustedAllFormsPredictions = []
pushedAdjustedNRPredictions = []
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
        print('Skipping project: ' + projects[p]['projectName'] + ' due to missing baselineEndQuarter/implementationStartQuarter')
        continue

    baselinePeriods = get_previous_periods(projects[p]['baselineEndQuarter'],4)
    implementationPeriods = get_future_periods_todate(projects[p]['baselineEndQuarter'])
    implementationPeriods.sort()

    print(implementationPeriods)

    if(len(implementationPeriods) == 0):
         print('No implementation period exists to calculate unadjusted additionality')
         continue

    unadjustedAdditionalityPeriods = baselinePeriods + implementationPeriods
    numberOfPastQuartersForUnadjustedAdditionality = len(unadjustedAdditionalityPeriods)
    unadjustedAdditionalityPeriods.sort()

    adjustedAdditionalityBaselinePeriods = get_previous_periods(projects[p]['baselineEndQuarter'],numberOfPastQuartersForAdjustedAdditionality)
    adjustedAdditionalityBaselinePeriods.sort()

    adjustedAdditionalityOutputPeriods = adjustedAdditionalityBaselinePeriods + get_future_periods(projects[p]['baselineEndQuarter'],numberOfFutureQuartersForAdjustedAdditionality)
    adjustedAdditionalityOutputPeriods.sort()

    adjustedAdditionalityBaselinePeriodString = ''
    for i in range (len(adjustedAdditionalityBaselinePeriods)):
        adjustedAdditionalityBaselinePeriodString += '&period='+adjustedAdditionalityBaselinePeriods[i]

    print(unadjustedAdditionalityPeriods)
    print(adjustedAdditionalityBaselinePeriodString)

    unadjustedInputPeriodString = ''
    for i in range (len(unadjustedAdditionalityPeriods)):
        unadjustedInputPeriodString += '&period='+unadjustedAdditionalityPeriods[i]

    print("Fetching orgUnits under project: " + projects[p]['projectName'])
    porgs = d2get('organisationUnits.json?fields=id&filter=path:like:'+projects[p]['projectOrgUnitId']+'&paging=false','organisationUnits')
    
    # Add child orgUnitIds of project that are also attached to the dataSet
    orgUnits = [porg["id"] for porg in porgs if porg["id"] in dataSetOrgUnits_set ]

    print("Calculating unadjusted additionality for " + str(len(orgUnits)) + " orgUnits that are attached to DataSet in project: " + projects[p]['projectName'])

    for o in range(0, len(orgUnits), batch_size):
        orgUnitsBatched = orgUnits[o:o + batch_size]  # Slice the batch

        #clear dataValue if clearPeriods is specified
        deleteDataValues( adjustedAdditionalityOutputDataElementIds+unadjustedAdditionalityOutputDataElementIds+[adjustedAdditionalityAllFormsOutputDataElementId,unadjustedAdditionalityAllFormsOutputDataElementId],orgUnitsBatched)

        unadjustedInputDataValueResultMap = getDataValues(inputDataElementIds+[pulmonaryBOther,pulmonaryCDOther,extraPulmonaryOther],orgUnitsBatched,unadjustedInputPeriodString,True,unadjustedAdditionalityPeriods)
        adjustedInputDataValueResultMap = getDataValues(inputDataElementIds+[pulmonaryBOther,pulmonaryCDOther,extraPulmonaryOther],orgUnitsBatched,adjustedAdditionalityBaselinePeriodString,True,adjustedAdditionalityBaselinePeriods)
       
        unadjustedAllFormsDataValues = []
        unadjustedNRDataValues= []
        predictedAllFormsDataValues = []
        predictedNRDataValues= []


        for b in range (len(orgUnitsBatched)):
            orgUnit = orgUnitsBatched[b]
           
            if unadjustedInputDataValueResultMap.get(orgUnit) is None:
                skippedOrgUnits = skippedOrgUnits+1
                continue

            for d in range(len(inputDataElementIds)):
        
                inputDataElement = inputDataElementIds[d]
                unadjustedAdditionalityOutputDataElement = unadjustedAdditionalityOutputDataElementIds[d]
                adjustedAdditionalityOutputDataElement = adjustedAdditionalityOutputDataElementIds[d]
        
                if unadjustedInputDataValueResultMap[orgUnit].get(inputDataElement) is None:
                    skippedOrgUnits = skippedOrgUnits+1
                    continue

                unadjustedAdditionalityInputDataValuesForDE = unadjustedInputDataValueResultMap[orgUnit][inputDataElement]["dataValues"]
                adjustedAdditionalityInputDataValuesForDE = adjustedInputDataValueResultMap[orgUnit][inputDataElement]["dataValues"]

                if len(unadjustedAdditionalityInputDataValuesForDE)!=len(unadjustedAdditionalityPeriods):
                    print("Past unadjusted dataValues of " +str(inputDataElement)+ " is not matching the number of unadjusted baseline periods")
                    skippedUnadjustedNR.append(orgUnit+"-"+str(inputDataElement))
                    continue

                if len(adjustedAdditionalityInputDataValuesForDE)!=numberOfPastQuartersForAdjustedAdditionality:
                    print("Past adjusted dataValues of " +str(inputDataElement)+ " is not matching the number of adjusted baseline periods")
                    skippedAdjustedNRPredictions.append(orgUnit+"-"+str(inputDataElement))
                    continue

                unadjustedAdditionalities = calculateUnadjustedAdditionality(unadjustedAdditionalityInputDataValuesForDE,implementationPeriods)
                adjustedAdditionalities = calculatePredictions(quarter_numbers,adjustedAdditionalityInputDataValuesForDE,len(adjustedAdditionalityOutputPeriods))
                
                pushedUnadjustedNR.append(orgUnit+"-"+unadjustedAdditionalityOutputDataElement)
                pushedAdjustedNRPredictions.append(orgUnit+"-"+adjustedAdditionalityOutputDataElement)

                print(unadjustedAdditionalityInputDataValuesForDE)
                print(unadjustedAdditionalities)
                print(adjustedAdditionalityInputDataValuesForDE)
                print(adjustedAdditionalities)

                for o in range(len(implementationPeriods)):
                    dataValue = { "categoryOptionCombo": defaultOption,
                    "attributeOptionCombo": defaultOption,
                    "dataElement":unadjustedAdditionalityOutputDataElement,
                    "period":implementationPeriods[o],
                    "orgUnit": orgUnit,
                    "value": str(unadjustedAdditionalities[o])
                    }
    
                    unadjustedNRDataValues.append(dataValue)

                for o in range(len(adjustedAdditionalityOutputPeriods)):
                    dataValue = { "categoryOptionCombo": defaultOption,
                    "attributeOptionCombo": defaultOption,
                    "dataElement":adjustedAdditionalityOutputDataElement,
                    "period":adjustedAdditionalityOutputPeriods[o],
                    "orgUnit": orgUnit,
                    "value": str(adjustedAdditionalities[o])
                    }
    
                    predictedNRDataValues.append(dataValue)


        
            if unadjustedInputDataValueResultMap[orgUnit].get(pulmonaryBNR) is None or unadjustedInputDataValueResultMap[orgUnit].get(pulmonaryBOther) is None or unadjustedInputDataValueResultMap[orgUnit].get(pulmonaryCDNR) is None or unadjustedInputDataValueResultMap[orgUnit].get(pulmonaryCDOther) is None or unadjustedInputDataValueResultMap[orgUnit].get(extraPulmonaryNR) is None or unadjustedInputDataValueResultMap[orgUnit].get(extraPulmonaryOther) is None:
                print("Datavalue missing for one of allForms calculation. Skipping all forms unadjusted additionality for orgUnit:"+orgUnit)
                skippedUnadjustedAllForms.append(orgUnit)
                continue

            if adjustedInputDataValueResultMap[orgUnit].get(pulmonaryBNR) is None or adjustedInputDataValueResultMap[orgUnit].get(pulmonaryBOther) is None or adjustedInputDataValueResultMap[orgUnit].get(pulmonaryCDNR) is None or adjustedInputDataValueResultMap[orgUnit].get(pulmonaryCDOther) is None or adjustedInputDataValueResultMap[orgUnit].get(extraPulmonaryNR) is None or adjustedInputDataValueResultMap[orgUnit].get(extraPulmonaryOther) is None:
                print("Datavalue missing for one of allForms calculation. Skipping all forms prediction for orgUnit:"+orgUnit)
                skippedAdjustedAllFormsPredictions.append(orgUnit)
                continue
        
            unadjustedPulmonaryBNRDataValues = unadjustedInputDataValueResultMap[orgUnit][pulmonaryBNR]["dataValues"]
            unadjustedPulmonaryBOtherDataValues = unadjustedInputDataValueResultMap[orgUnit][pulmonaryBOther]["dataValues"]
            unadjustedPulmonaryCDNRDataValues  = unadjustedInputDataValueResultMap[orgUnit][pulmonaryCDNR]["dataValues"]
            unadjustedPulmonaryCDOtherDataValues = unadjustedInputDataValueResultMap[orgUnit][pulmonaryCDOther]["dataValues"]
            unadjustedExtraPulmonaryNRDataValues = unadjustedInputDataValueResultMap[orgUnit][extraPulmonaryNR]["dataValues"]
            unadjustedExtraPulmonaryOtherDataValues = unadjustedInputDataValueResultMap[orgUnit][extraPulmonaryOther]["dataValues"]
            if len(unadjustedPulmonaryBNRDataValues)!= numberOfPastQuartersForUnadjustedAdditionality or len(unadjustedPulmonaryBOtherDataValues)!= numberOfPastQuartersForUnadjustedAdditionality or len(unadjustedPulmonaryCDNRDataValues)!= numberOfPastQuartersForUnadjustedAdditionality or len(unadjustedPulmonaryCDOtherDataValues)!= numberOfPastQuartersForUnadjustedAdditionality or len(unadjustedExtraPulmonaryNRDataValues)!= numberOfPastQuartersForUnadjustedAdditionality or len(unadjustedExtraPulmonaryOtherDataValues)!= numberOfPastQuartersForUnadjustedAdditionality :
                print("Number of dataValues is not equals number of pastPeriods. Skipping all forms prediction for orgUnit:"+orgUnit)
                skippedUnadjustedAllForms.append(orgUnit)
                continue
        
            adjustedPulmonaryBNRDataValues = adjustedInputDataValueResultMap[orgUnit][pulmonaryBNR]["dataValues"]
            adjustedPulmonaryBOtherDataValues = adjustedInputDataValueResultMap[orgUnit][pulmonaryBOther]["dataValues"]
            adjustedPulmonaryCDNRDataValues  = adjustedInputDataValueResultMap[orgUnit][pulmonaryCDNR]["dataValues"]
            adjustedPulmonaryCDOtherDataValues = adjustedInputDataValueResultMap[orgUnit][pulmonaryCDOther]["dataValues"]
            adjustedExtraPulmonaryNRDataValues = adjustedInputDataValueResultMap[orgUnit][extraPulmonaryNR]["dataValues"]
            adjustedExtraPulmonaryOtherDataValues = adjustedInputDataValueResultMap[orgUnit][extraPulmonaryOther]["dataValues"]
           
            if len(adjustedPulmonaryBNRDataValues)!= len(adjustedAdditionalityBaselinePeriods) or len(adjustedPulmonaryBOtherDataValues)!= len(adjustedAdditionalityBaselinePeriods) or len(adjustedPulmonaryCDNRDataValues)!= len(adjustedAdditionalityBaselinePeriods) or len(adjustedPulmonaryCDOtherDataValues)!= len(adjustedAdditionalityBaselinePeriods) or len(adjustedExtraPulmonaryNRDataValues)!= len(adjustedAdditionalityBaselinePeriods) or len(adjustedExtraPulmonaryOtherDataValues)!= len(adjustedAdditionalityBaselinePeriods) :
                print("Number of dataValues is not equals number of pastPeriods. Skipping all forms prediction for orgUnit:"+orgUnit)
                skippedAdjustedAllFormsPredictions.append(orgUnit)
                continue
        

            unadjustedAllFormsTotal = []
            for l in range(len(unadjustedPulmonaryBNRDataValues)):
                unadjustedAllFormsTotal.append(unadjustedPulmonaryBNRDataValues[l]+unadjustedPulmonaryBOtherDataValues[l]+unadjustedPulmonaryCDNRDataValues[l]+unadjustedPulmonaryCDOtherDataValues[l]+unadjustedExtraPulmonaryNRDataValues[l]+unadjustedExtraPulmonaryOtherDataValues[l])
        
            unadjustedAdditionalities = calculateUnadjustedAdditionality(unadjustedAllFormsTotal,implementationPeriods)
            print("All Forms values", unadjustedAllFormsTotal)
            print("AllForms UnadjustedAdditionality:"+str(unadjustedAdditionalities))

            adjustedAllFormsTotal = []
            for l in range(len(adjustedPulmonaryBNRDataValues)):
                adjustedAllFormsTotal.append(adjustedPulmonaryBNRDataValues[l]+adjustedPulmonaryBOtherDataValues[l]+adjustedPulmonaryCDNRDataValues[l]+adjustedPulmonaryCDOtherDataValues[l]+adjustedExtraPulmonaryNRDataValues[l]+adjustedExtraPulmonaryOtherDataValues[l])
        
            predictions = calculatePredictions(quarter_numbers,adjustedAllFormsTotal,len(adjustedAdditionalityOutputPeriods))
           

            for m in range(len(implementationPeriods)):
                dataValue = { "categoryOptionCombo": defaultOption,
                    "attributeOptionCombo": defaultOption,
                    "dataElement":unadjustedAdditionalityAllFormsOutputDataElementId,
                    "period":implementationPeriods[m],
                    "orgUnit": orgUnit,
                    "value": str(unadjustedAdditionalities[m])
                }
                unadjustedAllFormsDataValues.append(dataValue)

            pushedUnadjustedAllForms.append(orgUnit)

            for m in range(len(adjustedAdditionalityOutputPeriods)):
                dataValue = { "categoryOptionCombo": defaultOption,
                    "attributeOptionCombo": defaultOption,
                    "dataElement":unadjustedAdditionalityAllFormsOutputDataElementId,
                    "period":adjustedAdditionalityOutputPeriods[m],
                    "orgUnit": orgUnit,
                    "value": str(predictions[m])
                }
                predictedAllFormsDataValues.append(dataValue)

            pushedAdjustedAllFormsPredictions.append(orgUnit)

        payload= {}
        payload['dataValues'] = unadjustedNRDataValues + unadjustedAllFormsDataValues + predictedNRDataValues + predictedAllFormsDataValues
        #print('Pushing dataValues with Payload='+str(payload))
        
        status = d2post("dataValueSets.json",payload)
        print(status)
        coveredOrgUnits = coveredOrgUnits+len(orgUnitsBatched);
        print("Completed no. of orgunits="+str(coveredOrgUnits))

    



print("**********************")
print("Unadjusted Additionalities Run Summary")
print("Total AllForms Unadjusted Additionalities pushed:"+str(len(pushedUnadjustedAllForms)))
print("Total NR Unadjusted Additionalities pushed:"+str(len(pushedUnadjustedNR)))
print("Total AllForms Unadjusted Additionalities skipped due to missing data:"+str(len(skippedUnadjustedAllForms)))
print("Total NR Unadjusted Additionalities skipped due to missing data:"+str(len(skippedUnadjustedNR)))
print("**********************")
print("Skip Summary")
print("All Forms Unadjusted Additionalities Skipped For OrgUnits")
print(skippedUnadjustedAllForms)
print("NR Unadjusted Additionalities Skipped for OrgUnits")
print(skippedUnadjustedNR)
print("**********************")
print("Push Summary")
print("All Forms Unadjusted Additionalities Pushed for OrgUnits")
print(pushedUnadjustedAllForms)
print("NR Unadjusted Additionalities Pushed for OrgUnits")
print(pushedUnadjustedNR)


