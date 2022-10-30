import boto3
import datetime
import os

def lambda_handler(event, context):
    bucket = os.environ['myStaticS3']
    websiteMessage = os.environ['websiteMessage']
    mySSMParameterStore = os.environ['mySSMParameterStore']
    
    tme = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    boto3.resource('s3').Bucket(bucket ).put_object(
        ACL         = 'bucket-owner-full-control',
        ContentType = 'text/html',
        Key         = 'index.html',
        Body        = f'''<html><h1>Lambda function</h1>
            <li>Hello - the time is {tme} - this means we can write to <b>myStaticS3</b></li>
            <li>The websiteMessage (CloudFormation Parameter is <b>{websiteMessage}</b></li>
            <li>The <b>mySSMParameterStore</b> value is <b>{mySSMParameterStore}</b></li>

            </html>
            '''
    )

    return { 'statusCode': 200, 'body': 'ok' }