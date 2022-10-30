import boto3
import uuid

def lambda_handler(event, context):
    TableName = 'myDynamoDbTable'
    
    boto3.resource('dynamodb').Table(TableName).put_item(
        Item={
            'id' : str(uuid.uuid4()),
            'event' : event
        })
    
    return { 'statusCode': 200, 'body': 'ok' }