from __future__ import print_function
import urllib3
import json
import boto3

#Deletes ApiGateway ACM Cname that was created automatically on stack creation

#INPUTS: CertificateArn, R53ZoneId

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

acm_client = boto3.client('acm')
r53_client = boto3.client('route53')

def lambda_handler(event, context):

    #Set vars from event properties    
    R53ZoneId = event['ResourceProperties']['R53ZoneId']
    CertificateArn = event['ResourceProperties']['CertificateArn']

    if event['RequestType'] == "Delete":
        
        #Initialize vars outside try block
        CNAME = ""
        Value = ""
        
        try:
            #describe certificate to extract CNAME info
            describe_response = acm_client.describe_certificate(
                CertificateArn=CertificateArn
            )
            
            #exctract CNAME and Value from cert describe
            CNAME = describe_response['Certificate']['DomainValidationOptions'][0]['ResourceRecord']['Name']
            Value = describe_response['Certificate']['DomainValidationOptions'][0]['ResourceRecord']['Value']
            
        
        except Exception as e:
            responseData = {
                "FailReason" : "Certificate describe failed"
            }
            STATUS = "FAILED"
                        
        try:
            #Delete CNAME
            r53_response = r53_client.change_resource_record_sets(
                HostedZoneId=R53ZoneId,
                ChangeBatch= {
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': 
                                {
                                    'Name': CNAME,
                                    'Type': 'CNAME',
                                    'TTL': 300,
                                    'ResourceRecords': [{'Value': Value}]
                                }
                        }
                    ]
                }
            )
            
            STATUS = "SUCCESS"
            
            responseData = {
                "SUCCESS" : "Successfully deleted ApiGateway ACM CNAME from R53"
            }
                        
        except Exception as e:
            responseData = {
                "FailReason" : "R53 ACM CNAME delete failed",
                "cname" : CNAME,
                "cnameval" : Value,
                "r53zoneid" : R53ZoneId
            }
            STATUS = "FAILED"
                
        send(event, context, STATUS, responseData)
        
    else:
        responseData = {
                "SUCCESS" : "This was not a delete request no action needed"
            }
        send(event, context, SUCCESS, responseData)