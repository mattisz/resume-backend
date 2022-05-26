from __future__ import print_function
import urllib3
import time
import json
import boto3

#creates ACM certificate in us-east-1 for cloudfront regardless of region stack is deployed to

#INPUTS: DomainName, R53ZoneId
#Outputs: CertificateArn, CNAME, Value

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

cfn_client = boto3.client('cloudformation')
acm_client = boto3.client('acm', region_name='us-east-1')
r53_client = boto3.client('route53')

def lambda_handler(event, context):
    
    #set timeout for while loop
    expire_epoch = int(time.time()) + 300
    
    #Set vars from event properties
    domain = event['ResourceProperties']['DomainName']
    R53ZoneId = event['ResourceProperties']['R53ZoneId']
    stackId = event['StackId']
        
    if event['RequestType'] == "Create":
    
        try:
            #request certificate
            req_response = acm_client.request_certificate(
                DomainName=domain,
                ValidationMethod='DNS',
                IdempotencyToken='lambdaACMReq',
                Options={
                    'CertificateTransparencyLoggingPreference': 'ENABLED'
                }
            )
        except Exception as e:
            responseData = {
                "FailReason" : "Certificate request failed"
            }
            send(event, context, FAILED, responseData)
        
        while int(time.time()) < expire_epoch:
            
            #intialize vars outside try block
            CNAME = ""
            Value = ""
            
            try:
                #describe certificate
                describe_response = acm_client.describe_certificate(
                    CertificateArn=req_response['CertificateArn']
                )
                
                # extract cname and value from certificate describe
                CNAME = describe_response['Certificate']['DomainValidationOptions'][0]['ResourceRecord']['Name']
                Value = describe_response['Certificate']['DomainValidationOptions'][0]['ResourceRecord']['Value']
                
            
            except Exception as e:
                responseData = {
                    "FailReason" : "Certificate describe failed"
                }
                STATUS = "FAILED"
                
            try:
                #add R53 CNAME record to validate ACM certificate
                r53_response = r53_client.change_resource_record_sets(
                    HostedZoneId=R53ZoneId,
                    ChangeBatch= {
                        'Changes': [
                            {
                                'Action': 'UPSERT',
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
                    "certificateArn" : req_response['CertificateArn'],
                    "certificateCname" : CNAME,
                    "certificateCnameValue" : Value,
                    "r53ZoneId" : R53ZoneId
                }
                
                break
                
            except Exception as e:
                responseData = {
                    "FailReason" : "R53 record create failed",
                    "cname" : CNAME,
                    "cnameval" : Value,
                    "r53zoneid" : R53ZoneId
                }
                STATUS = "FAILED"
                
        send(event, context, STATUS, responseData)
        
    elif event['RequestType'] == "Delete":
        
        #initialize vars outside try block
        certArn = ""
        cname = ""
        value = ""
        r53zoneid = ""
        
        try:
            #describe the stack
            cfn_response = cfn_client.describe_stacks(
                StackName=stackId
            )

            #get outputs from stack describe
            outputs = cfn_response['Stacks'][0]['Outputs']

            #set vars from outputs
            for output in outputs:
                if output['OutputKey'] == 'certificateArn':
                    certArn = output['OutputValue']
                elif output['OutputKey'] == 'certificateCname':
                    cname = output['OutputValue']
                elif output['OutputKey'] == 'certificateCnameValue':
                    value = output['OutputValue']
                elif output['OutputKey'] == 'r53ZoneId':
                    r53zoneid = output['OutputValue']
            
        except Exception as e:
            responseData = {
                "FailReason" : "Stack describe failed",
                "Stackid" : stackId
            }
            send(event, context, FAILED, responseData)
            
        try:
            #delete certificate
            delete_response = acm_client.delete_certificate(
                CertificateArn=certArn
            )
        except Exception as e:
            responseData = {
                "FailReason" : "Delete certificate failed"
            }
            send(event, context, FAILED, responseData)
            
        try:
            #delete validation CNAME from R53
            r53_response = r53_client.change_resource_record_sets(
                HostedZoneId=r53zoneid,
                ChangeBatch= {
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': 
                                {
                                    'Name': cname,
                                    'Type': 'CNAME',
                                    'TTL': 300,
                                    'ResourceRecords': [{'Value': value}]
                                }
                        }
                    ]
                }
            )
        
            responseData = {
                    "SUCCESS" : "Successfully deleted certificate and R53 CNAME"
                }
            send(event, context, SUCCESS, responseData)
        
        except Exception as e:
            responseData = {
                "FailReason" : "Delete R53 CNAME failed",
                "certArn" : certArn,
                "cname" : cname,
                "value" : value,
                "r53zoneid" : r53zoneid
            }
            send(event, context, FAILED, responseData)
        
    #ignore if not create or delete request
    else:
        responseData = {
                "SUCCESS" : "This was neither a create or delete request"
            }
        send(event, context, SUCCESS, responseData)