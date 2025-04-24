# kit-python-script

Sample Configuration file (.conf) for the bestFit script

{
   "dhis": {
     "baseurl": "https://<baseurl>",
     "username": "username",
     "password": "password",
     "inputDataElementIds":["dataElementIdOfPTBBac+NR","dataElementIdOfPTBCDNR","dataElementIdOfEPTBNR"],
     "outputDataElementIds": ["dataElementIdOfPTBBac+NRPrediction","dataElementIdOfPTBCDNRPrediction","dataElementIdOfEPTBNRPrediction"],
     "defaultOption": "HllvX50cXC0",
     "period":"2024Q3",
     "numberOfPastQuarters":12,
     "numberOfFutureQuarters":5,
     "dataSetIds": ["<dataSetIdOfPivot>","<dataSetIdOfPivot*>"],
     "pulmonaryBNR":"<dataElementId>",
     "pulmonaryBOther":"<dataElementId>",
     "pulmonaryCDNR":"<dataElementId>",
     "pulmonaryCDOther":"<dataElementId>",
     "extraPulmonaryNR":"<dataElementId>",
     "extraPulmonaryOther":"<dataElementId>",
     "allFormsOutputDataElementId":"<dataElementId>"
   }
 }
