from __future__ import print_function
import urllib3
import json
import boto3
import time

#Updates NS on base domain R53 to point to new Route53 hosted zone

#INPUTS: DomainName, R53ZoneId, R53NameServers, BaseDomainRoleArn

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



def lambda_handler(event, context):

    sts_client = boto3.client('sts')
    
    epoch = time.time()
    
    #Set vars from event properties
    domain = event['ResourceProperties']['DomainName'].lower()
    R53ZoneId = event['ResourceProperties']['BaseDomainR53ZoneId']
    R53NameServers = event['ResourceProperties']['R53NameServers']
    BaseDomainRoleArn = event['ResourceProperties']['BaseDomainRoleArn']

    SessionName = "ResumeBaseNSLambda-" + str(epoch)

    #Assumes role in base domain account to allow NS record updates
    assumed_role_object=sts_client.assume_role(
        RoleArn=BaseDomainRoleArn,
        RoleSessionName=SessionName
    )

    credentials=assumed_role_object['Credentials']

    r53_client = boto3.client(
        'route53',
        aws_access_key_id=credentials['AccessKeyId'],
        aws_secret_access_key=credentials['SecretAccessKey'],
        aws_session_token=credentials['SessionToken']
    )
        
    if event['RequestType'] == "Create":
           
        try:
            #Creates NS record for the R53 hosted zone on stack create
            r53_response = r53_client.change_resource_record_sets(
                HostedZoneId=R53ZoneId,
                ChangeBatch= {
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet': 
                                {
                                    'Name': domain,
                                    'Type': 'NS',
                                    'TTL': 300,
                                    'ResourceRecords': [
                                        {'Value': R53NameServers[0]},
                                        {'Value': R53NameServers[1]},
                                        {'Value': R53NameServers[2]},
                                        {'Value': R53NameServers[3]}
                                    ]
                                }
                        }
                    ]
                }
            )
            
            STATUS = "SUCCESS"
            
            responseData = {
                "Sucess" : f"Sucessfully created NS records on base hosted zone. ID: {R53ZoneId}"
            }
            
        except Exception as e:
            responseData = {
                "Fail Reason": f"Failed to create NS records on base hosted zone. ID: {R53ZoneId}"
            }
            STATUS = "FAILED"
            
        send(event, context, STATUS, responseData)
        
    elif event['RequestType'] == "Delete":
        
        try:
            #Deletes NS record for the R53 hosted zone on stack delete
            r53_response = r53_client.change_resource_record_sets(
                HostedZoneId=R53ZoneId,
                ChangeBatch= {
                    'Changes': [
                        {
                            'Action': 'DELETE',
                            'ResourceRecordSet': 
                                {
                                    'Name': domain,
                                    'Type': 'NS',
                                    'TTL': 300,
                                    'ResourceRecords': [
                                        {'Value': R53NameServers[0]},
                                        {'Value': R53NameServers[1]},
                                        {'Value': R53NameServers[2]},
                                        {'Value': R53NameServers[3]}
                                    ]
                                }
                        }
                    ]
                }
            )
        
            responseData = {
                    "SUCCESS" : f"Successfully deleted NS records on base hosted zone. ID: {R53ZoneId}"
                }
            send(event, context, SUCCESS, responseData)
        
        except Exception as e:
            responseData = {
                "Fail Reason": f"Failed to delete NS records on base hosted zone. ID: {R53ZoneId}"
            }

            send(event, context, FAILED, responseData)
        
    else:
        responseData = {
                "SUCCESS" : "This was neither a create or delete request"
            }
        send(event, context, SUCCESS, responseData)