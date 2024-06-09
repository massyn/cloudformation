import json
import boto3
from botocore.exceptions import ClientError

import urllib.request
import urllib.parse

def findIps():
    req = urllib.request.Request(
        'https://api.cloudflare.com/client/v4/ips',
        headers = 
        {   'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())
    
def update_bucket_policy(bucket_name,ip):
    print(f"Updating bucket policy : {bucket_name}")
    policy = {
        "Version": "2008-10-17",
        "Id": "PolicyForCloudFlareContent",
        "Statement": [
            {
                "Sid" : "3",
                "Effect" : "Allow",
                "Principal" : "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*",
                "Condition": {
                    "IpAddress": {
                        "aws:SourceIp": 
                            ip['ipv4_cidrs'] + 
                            ip['ipv6_cidrs']
                    }
                }
            }
        ]
    }
    
    boto3.client('s3').put_bucket_policy(Bucket=bucket_name, Policy=json.dumps(policy))

def find_buckets():
    result = []
    s3 = boto3.client('s3')
    for page in s3.list_buckets()['Buckets']:
        print(page['Name'])
        tags = {}
        try:
            for t in s3.get_bucket_tagging(Bucket=page['Name'])['TagSet']:
                tags[t['Key']] = t['Value']
            print(tags)
        except ClientError:
            print(" - no tags")

        if tags.get('cloudflare') == 'true':
            result.append(page['Name'])
    return result

def lambda_handler(event, context):
    ip = findIps()['result']
    buckets = find_buckets()
    for bucket in buckets:
        update_bucket_policy(bucket,ip)

    return {
        'statusCode': 200,
        'body': json.dumps({ 'buckets' : buckets})
    }
