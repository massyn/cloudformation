import boto3
import datetime
import os

def lambda_handler(event, context):
    bucket = os.environ['myStaticSite']
    
    tme = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    boto3.resource('s3').Bucket(bucket ).put_object(
        ACL         = 'bucket-owner-full-control',
        ContentType = 'text/html',
        Key         = 'index.html',
        Body        = f'Hello - the time is {tme}'
    )

    return { 'statusCode': 200, 'body': 'ok' }