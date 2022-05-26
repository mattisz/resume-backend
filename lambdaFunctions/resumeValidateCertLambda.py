from __future__ import print_function
import urllib3
import time
import json
import boto3

#Checks to make sure Cloudfront ACM certificate (created by resumeCloudfrontACMLambda.py) is validated
#This occurs before Cloudfront distribution creation

#INPUTS: certificateArn

## start cfnresponse module source code ##
SUCCESS = "SUCCESS"
FAILED = "FAILED"

http = urllib3.PoolManager()


def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=None):
    responseUrl = event['ResponseURL']

    print(responseUrl)

    responseBody = {
        'Status' : responseStatus,
        'Reason' : reason or "See the details in CloudWatch Log Stream: {}".format(context.log_stream_name),
        'PhysicalResourceId' : physicalResourceId or context.log_stream_name,
        'StackId' : event['StackId'],
        'RequestId' : event['RequestId'],
        'LogicalResourceId' : event['LogicalResourceId'],
        'NoEcho' : noEcho,
        'Data' : responseData
    }

    json_responseBody = json.dumps(responseBody)

    print("Response body:")
    print(json_responseBody)

    headers = {
        'content-type' : '',
        'content-length' : str(len(json_responseBody))
    }

    try:
        response = http.request('PUT', responseUrl, headers=headers, body=json_responseBody)
        print("Status code:", response.status)


    except Exception as e:

        print("send(..) failed executing http.request(..):", e)
## end cfnresponse module souce code ##

acm_client = boto3.client('acm', region_name='us-east-1')

def lambda_handler(event, context):
    
    #Set timeout slightly shorter than lambda function timeout
    expire_epoch = int(time.time()) + 880
    
    #Set vars from event context
    certificateArn = event['ResourceProperties']['certificateArn']
        
    if event['RequestType'] == "Create":
        
        while int(time.time()) < expire_epoch:
            
            #initialize vars outside try block
            validationStatus = ""
            STATUS = None
            
            try:
                #describe the certificate by ARN
                describe_response = acm_client.describe_certificate(
                    CertificateArn=certificateArn
                )
                
                #get the validation status of the certificate
                validationStatus = describe_response['Certificate']['DomainValidationOptions'][0]['ValidationStatus']
            
            except Exception as e:
                responseData = {
                    "FailReason" : "Certificate describe failed"
                }
                STATUS = "FAILED"
                
            #break out of loop on successful validation
            if validationStatus == "SUCCESS":
                responseData = {
                    "SUCCESS" : "Certificate was successfully validated"
                }
                STATUS = "SUCCESS"
                break
            
            #break out of loop if validation fails
            elif validationStatus == "FAILED":
                responseData = {
                    "FailReason" : "Certificate was unable to validate"
                }
                STATUS = "FAILED"
                break
        
        #return failure if lambda function times out
        if STATUS == None:
            responseData = {
                    "FailReason" : "Certificate still pending validation. Lambda function timed out."
                }
            STATUS = "FAILED"
        
        send(event, context, STATUS, responseData)
        
    #ignore if not a creation request
    else:
        responseData = {
                "SUCCESS" : "This was not a create request. Validation not required."
            }
        send(event, context, SUCCESS, responseData)