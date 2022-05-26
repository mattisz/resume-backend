import json
import boto3
import hashlib
import os

#visitor counter function to display on website

#sets table_name from environment variable
table_name = os.environ['tableName']

client = boto3.client('dynamodb')

def lambda_handler(event, context):
    
    #gets user ip from event context
    plain_ip = event['requestContext']['http']['sourceIp']
    #hashes the ip before storing in DynamoDB table
    ip = hashlib.sha256(plain_ip.encode('utf-8')).hexdigest()
    
    #gets the user's visitor history based on hashed ip
    get_user = client.get_item(
        TableName=table_name,
        Key={
            'IP': {
                'S': ip
            }
        }
    )
    
    #gets the total number of visitors to the site
    get_total = client.get_item(
        TableName=table_name,
        Key={
            'IP': {
                'S': 'Total'
            }
        }
    )
    
    #tries to get the total number of visitors to the site, if this is the first visitor sets to 0
    try:
        current_total = int(get_total["Item"]["numVisits"]["N"])
    except KeyError:
        current_total = 0
        
    #tries to get the number of visits for this ip address, if this is the first visit sets to 1
    try:
        user_num_visits = int(get_user["Item"]["numVisits"]["N"]) + 1
    except KeyError:
        user_num_visits = 1

    #updates total visitors  if this IP first visit  
    if user_num_visits == 1:
        total_visitors = current_total + 1
        update_total = client.put_item(
        TableName=table_name,
        Item={
            'IP': {
                'S': 'Total'
            },
            'numVisits': {
                'N': str(total_visitors)
            }
        }
    )
    else:
        total_visitors = current_total
    
    #updates the number of visits for this hashed ip address
    update_user = client.put_item(
        TableName=table_name,
        Item={
            'IP': {
                'S': ip
            },
            'numVisits': {
                'N': str(user_num_visits)
            }
        }
    )
    
    #returns the total visits for this ip and the total number of visitors
    response = {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Allow-Origin': '*.mattisz.com/*',
            'Access-Control-Allow-Methods': 'OPTIONS,POST,GET',
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'user_visits':user_num_visits,
            'total_visitors':total_visitors
        })
    }
    
    return response