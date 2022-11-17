import json
import os
import argparse
import boto3
import re
   

# =========================== Resource Templates ===========================

def resourceTemplate(name,type,**KW):
    def check(KW,p):
        if not p in KW:
            log("FATAL",f"PARAM {p} is missing")
        else:
            if KW[p] == None:
                log("FATAL",f"PARAM {p} is blank")
        log("INFO",f" - Parameter {p} = {KW[p]}")

    log("INFO",f"ResourceTemplate : Adding resource {type} ({name})")
    if type == "vpc":
        check(KW,'cidr')
        return  {
            "Type" : "AWS::EC2::VPC",
            "Properties" : {
                "CidrBlock" : KW['cidr'],
                "EnableDnsHostnames" : True,
                "EnableDnsSupport" : True,
                "InstanceTenancy" : "default"
            }
        }
    elif type == "igw":   
        return {
            "Type" : "AWS::EC2::InternetGateway",
            "Properties" : {}
        }
    elif type == "igwattachment":
        check(KW,'InternetGatewayId')
        check(KW,'vpc')
        return {
            "Type" : "AWS::EC2::VPCGatewayAttachment",
            "Properties" : {
                "InternetGatewayId" : { "Ref" : KW['InternetGatewayId'] },
                "VpcId" : { "Ref" : KW['vpc'] }
            },
            "DependsOn" : [ KW['InternetGatewayId'], KW['vpc'] ],
        }
    elif type == 'routetable':
        check(KW,'vpc')
        return {
            "Type" : "AWS::EC2::RouteTable",
            "Properties" : {
                "VpcId" : { "Ref" : KW['vpc'] },
                "Tags" : [
                    {
                    "Key" : "Name",
                    "Value" : name
                    }
                ],
            },
            "DependsOn" : [ KW['vpc'] ]
        }
    elif type == 'routeigw':
        check(KW,'InternetGatewayId')
        check(KW,'RouteTableId')
        return {
            "Type" : "AWS::EC2::Route",
            "Properties" : {
                "RouteTableId" : { "Ref" : KW['RouteTableId']  },
                "DestinationCidrBlock" : "0.0.0.0/0",
                "GatewayId" : { "Ref" : KW['InternetGatewayId'] },
            },
            "DependsOn" : [ KW['InternetGatewayId'], KW['RouteTableId'] ]
        }
    elif type == 'routenatgw':
        check(KW,'RouteTableId')
        check(KW,'NatGatewayId')
        return {
            "Type" : "AWS::EC2::Route",
            "Properties" : {
                "RouteTableId" : { "Ref" :  KW['RouteTableId']  },
                "DestinationCidrBlock" : "0.0.0.0/0",
                "NatGatewayId" : { "Ref" : KW['NatGatewayId'] },
            },
            "DependsOn" : [ KW['NatGatewayId'], KW['RouteTableId'] ]
        }
    elif type == 'subnet':
        check(KW,'vpc')
        check(KW,'cidr')
        check(KW,'az')
        check(KW,'MapPublicIpOnLaunch')
        return {
            "Type" : "AWS::EC2::Subnet",
            "Properties" : {
                "VpcId" : { "Ref" : KW['vpc'] },
                "CidrBlock" : KW['cidr'],
                "AvailabilityZone" : { "Fn::Select" : [  KW['az'], { "Fn::GetAZs" : "" } ] },
                "MapPublicIpOnLaunch" : KW['MapPublicIpOnLaunch'],
                "Tags" : [
                    {
                    "Key" : "Name",
                    "Value" : name
                    }
                ]
            }
        }
    elif type == 'subnetroute':
        check(KW,'RouteTableId')
        check(KW,'SubnetId')
        return {
            "Type" : "AWS::EC2::SubnetRouteTableAssociation",
            "Properties" : {
                "RouteTableId" : { "Ref" : KW['RouteTableId'] },
                "SubnetId" : { "Ref" : KW['SubnetId'] }
            },
            "DependsOn" : [ KW['RouteTableId'], KW['SubnetId']]
        }
    elif type == 'securitygroup':
        check(KW,'vpc')
        return {
            "Type": "AWS::EC2::SecurityGroup",
            "Properties": {
                "GroupDescription": "Security Group",
                "SecurityGroupIngress" : [],
                "SecurityGroupEgress" : [],
                "VpcId": { "Ref": KW['vpc'] },
                "Tags" : [
                    {
                    "Key" : "Name",
                    "Value" : name
                    }
                ],
            }
        }
    elif type == 's3':
        return {
            "Type": "AWS::S3::Bucket",
            "Properties" : {
                "AccessControl": "BucketOwnerFullControl",
                "PublicAccessBlockConfiguration": {
                    "BlockPublicAcls": True,
                    "BlockPublicPolicy": True,
                    "IgnorePublicAcls": True,
                    "RestrictPublicBuckets": True
                }
            }
        }
    elif type == 'static':
        return {
            "Type": "AWS::S3::Bucket",
            "Properties" : {
                "AccessControl": "PublicRead",
                "WebsiteConfiguration" : {
                    "IndexDocument": "index.html",
                    "ErrorDocument": "error.html"
                }
            },
            "DeletionPolicy": "Delete"
        }
    elif type == 'staticbucketpolicy':
        check(KW,'Bucket')
        return {
            "Type": "AWS::S3::BucketPolicy",
            "Properties": {
                "Bucket": { "Ref" : KW['Bucket']},
                "PolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": {
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": { "Fn::Join": [ "", [ "arn:" , { "Ref" : "AWS::Partition"} , ":s3:::", { "Ref": KW['Bucket'] }, "/*" ] ] },
                    }
                }
            },
            "DependsOn" : [ KW['Bucket'] ]
        }
    elif type == 'eip':
        return  {
            "Type" : "AWS::EC2::EIP",
            "Properties" : {
                "Domain" : "vpc"
            }
        }
    elif type == 'natgateway':
        check(KW,'eip')
        check(KW,'subnet')
        return {
            "Type" : "AWS::EC2::NatGateway",
            "Properties" : {
                "AllocationId" : { "Fn::GetAtt" : [ KW['eip'], "AllocationId"] },
                "SubnetId" : { "Ref" : KW['subnet'] },
            }
        }
    elif type == 'autoscaling':
        check(KW,'LaunchTemplateId')
        check(KW,'VPCZoneIdentifier')
        check(KW,'TargetGroupARNs')
        return {
            "Type" : "AWS::AutoScaling::AutoScalingGroup",
            "Properties" : {
                "AutoScalingGroupName" : name,
                "DesiredCapacity"   : 1,
                "LaunchTemplate" : {
                    "LaunchTemplateId" : { "Ref" : KW['LaunchTemplateId'] },
                    "Version" : { "Fn::GetAtt": [ KW['LaunchTemplateId'], "LatestVersionNumber" ] }
                },
                "VPCZoneIdentifier" : KW['VPCZoneIdentifier'],
                "MaxSize" : 1,
                "MinSize" : 1,
                "TargetGroupARNs" : [{ "Ref" : KW['TargetGroupARNs'] }]
            },
            "DependsOn" : [ KW['LaunchTemplateId'] ]
        }
    elif type == 'targetgroup':
        check(KW,'vpc')
        return {
            "Type" : "AWS::ElasticLoadBalancingV2::TargetGroup",
            "Properties" : {
                "Name" : name,
                "HealthCheckEnabled" : True,
                "HealthyThresholdCount" : 2,
                "HealthCheckTimeoutSeconds" : 20,
                "VpcId" : { "Ref" : KW['vpc'] },
                "Port" : 80,
                "Protocol" : "HTTP",
                "Matcher" : {
                    "HttpCode" : "200,302"
                }
            },
            "DependsOn" : [ KW['vpc'] ]
        }
    elif type == 'launchtemplate':
        check(KW,'IamInstanceProfile')
        check(KW,'ImageId')
        check(KW,'SecurityGroup')
        return {
            "Type":"AWS::EC2::LaunchTemplate",
            "Properties":{
                "LaunchTemplateName":name,
                "LaunchTemplateData":{
                    "IamInstanceProfile":{ "Arn":{"Fn::GetAtt": [ KW['IamInstanceProfile'], "Arn"]} },
                    "DisableApiTermination":"true",
                    "ImageId": { "Ref" : KW['ImageId'] },
                    "InstanceType":"t2.micro",
                    "BlockDeviceMappings":[{
                        "Ebs":{
                            "VolumeSize":"8",
                            "VolumeType":"gp2",
                            "DeleteOnTermination": True,
                            "Encrypted": True
                        },
                        "DeviceName": "/dev/xvda",
                    }],
                    "UserData"              : { "Fn::Base64" : { "Fn::Join" : ["\n", [
                        "#!/usr/bin/bash",
                        "yum update -y"
                    ]]}},
                    "SecurityGroupIds" : [ { "Ref" : KW['SecurityGroup'] } ]  
                }
            },
            "DependsOn" : [
                KW['IamInstanceProfile']
            ]
        }
    elif type == 'instanceprofile':
        check(KW,'Role')
        return {
            "Type": "AWS::IAM::InstanceProfile",
            "Properties": {
                "Path": "/",
                "Roles": [ { "Ref": KW['Role'] } ]
            },
            "DependsOn" : [ KW['Role'] ]
        }
    elif type == 'ec2role':
        return {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": { "Service": [  "ec2.amazonaws.com" ] },
                            "Action": [ "sts:AssumeRole" ]
                        }
                    ]
                },
                "Path": "/",
                "ManagedPolicyArns" : [
                    "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
                ]
            }
        }
    elif type == 'ec2instance':
        check(KW,'IamInstanceProfile')
        check(KW,'ImageId')
        check(KW,'SecurityGroup')
        check(KW,'Subnet')
        return {
            "Type" : "AWS::EC2::Instance",
            "Properties" : {
                "ImageId" : { "Ref" : KW['ImageId'] },
                "IamInstanceProfile"    : { "Ref" : KW['IamInstanceProfile'] },
                "InstanceType" : "t2.micro",
                "NetworkInterfaces": [ {
                    #"AssociatePublicIpAddress": "true",
                    "DeviceIndex": "0",
                    "GroupSet": [{ "Ref" : KW['SecurityGroup'] }],
                    "SubnetId": { "Ref" : KW['Subnet'] }
                } ],
                "BlockDeviceMappings":[{
                    "Ebs":{
                        "VolumeSize":"8",
                        "VolumeType":"gp2",
                        "DeleteOnTermination": True,
                        "Encrypted": True
                    },
                    "DeviceName": "/dev/xvda",
                }],
                "Tags" : [
                    {
                    "Key" : "Name",
                    "Value" : name
                    }
                ],
                "UserData"              : { "Fn::Base64" : { "Fn::Join" : ["\n", [
                        "#!/usr/bin/bash",
                        "yum update -y"
                    ]]}},
            },
            "DependsOn" : [
                KW['IamInstanceProfile']
            ]
        }
    elif type == 'rds':
        check(KW,'MasterUsername')
        check(KW,"MasterUserPassword")
        check(KW,"sg")
        check(KW,'DBSubnetGroupName')
        return {
            "Type": "AWS::RDS::DBInstance",
            "Properties" : {
                "DBName" : name,
                "AllocatedStorage": 20,
                "DBInstanceClass" : "db.t3.micro",
                "AutoMinorVersionUpgrade": True,
                "Engine" : "mysql",
                "MasterUsername" : { "Ref" : KW["MasterUsername"] },
                "MasterUserPassword" : { "Ref" : KW['MasterUserPassword'] },
                "MultiAZ" : False,
                "VPCSecurityGroups" : [ { "Ref" : KW['sg'] } ],
                "DBSubnetGroupName" : { "Ref" : KW['DBSubnetGroupName'] } 
            }
        }
    elif type == 'dbsubnetgroup':
        check(KW,"DBSubnetGroupDescription")
        check(KW,'subnet')
        SubnetIds = []
        for s in KW['subnet']:
            SubnetIds.append({ "Ref" : s})
        return {
            "Type": "AWS::RDS::DBSubnetGroup",
            "Properties": {
                "DBSubnetGroupDescription" : KW['DBSubnetGroupDescription'],
                "SubnetIds": SubnetIds,
            }
        }
    elif type == 'lambdaexecutionrole':
        return {
            "Type": "AWS::IAM::Role",
            "Properties": {
                "AssumeRolePolicyDocument": {
                    "Version": "2012-10-17",
                    "Statement": [{ "Effect": "Allow", "Principal": {"Service": ["lambda.amazonaws.com"]}, "Action": ["sts:AssumeRole"] }]
                },
                "Path": "/",
                "Policies": [{
                    "PolicyName" : { "Fn::Sub": f"${{AWS::StackName}}-{name}" },
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            { "Effect": "Allow", "Action": ["logs:CreateLogGroup", "logs:CreateLogStream" , "logs:PutLogEvents"], "Resource": "arn:aws:logs:*:*:*" }
                        ]
                    }
                }]
            }
        }
    elif type == 'lambda':
        check(KW,'Role')
        return {
            "Type": "AWS::Lambda::Function",
            "Properties": {
                "Handler": "index.lambda_handler",
                "Role": { "Fn::GetAtt": [ KW['Role'], "Arn" ] },
                "Description" : name,
                "Code": {
                    "ZipFile":  { "Fn::Join": ["\n", [
                        "import boto3",
                        "def lambda_handler(event, context):",
                        "    return { 'statusCode': 200, 'body': 'ok' }"
                    ]]}
                },
                "Runtime": "python3.9",
                "FunctionName": { "Fn::Sub": f"${{AWS::StackName}}-{name}" },
                "Timeout": 300,
                "TracingConfig": { "Mode": "Active" },
                "Environment": {
                    "Variables": {}
                }
            },
            "DependsOn" : [ KW['Role'] ]
        }
    elif type == 'eventbridgeschedule':
        check(KW,'cron')
        check(KW,'target')
        return {
            "Type": "AWS::Events::Rule",
            "Properties": {
                "Description": f"Scheduled event to trigger the Lambda function {KW['target']}",
                "ScheduleExpression" : KW['cron'],
                "State": "ENABLED",
                "Targets": [{ 
                    "Arn": { "Fn::GetAtt": [ KW['target'], "Arn" ] },
                    "Id" : { "Fn::Sub": f"${{AWS::StackName}}-{KW['target']}" }
                } ]
            }
        }
    elif type == 'lambdaeventbridgepermission':
        check(KW,'target')
        check(KW,'eventbridge')
        return {
            "Type": "AWS::Lambda::Permission",
            "Properties": {
                "FunctionName": { "Ref": KW['target'] },
                "Action": "lambda:InvokeFunction",
                "Principal": "events.amazonaws.com",
                "SourceArn": { "Fn::GetAtt": [ KW['eventbridge'], "Arn"] }
            },
            "DependsOn" : [
                KW['target'],
                KW['eventbridge']
            ]
        }
    elif type == 'functionurl':
        check(KW,'target')
        return {
            "Type" : "AWS::Lambda::Url",
            "Properties" : {
                "AuthType" : "NONE",
                "TargetFunctionArn" : { "Ref" : KW['target'] }
            }
        }
    elif type == 'lambdafunctionurlpublicpermission':
        check(KW,'target')
        return {
            "Type": "AWS::Lambda::Permission",
            "Properties": {
                "FunctionName": { "Ref": KW['target'] },
                "Action": "lambda:InvokeFunctionUrl",
                "Principal": "*",
                "FunctionUrlAuthType" : "NONE"
            }
        }
    elif type == 'ssmparameter':
        check(KW,'value')
        return {
            "Type": "AWS::SSM::Parameter",
            "Properties": {
                "Name": name,
                "Value": KW['value'],
                "Type": "String",
                "Description": name,
            }
        }
    elif type == 'elbv2':
        check(KW,'subnet')
        check(KW,'SecurityGroups')

        ss = []
        for s in KW['subnet']:
            ss.append({"Ref" : s })

        return {
            "Type" : "AWS::ElasticLoadBalancingV2::LoadBalancer",
            "Properties" : {
                "Scheme" : "internet-facing",
                "SecurityGroups" : [ { "Ref" : KW['SecurityGroups'] } ],
                
                "Subnets" : ss,
                "Type" : "application"
            },
            "DependsOn" : [
                KW['SecurityGroups']
            ]
        }
    elif type == 'elbv2listener':
        check(KW,'TargetGroupArn')
        check(KW,'LoadBalancerArn')
        return {
            "Type": "AWS::ElasticLoadBalancingV2::Listener",
            "Properties": {
                "DefaultActions": [],
                "DefaultActions" : [{
                    "Type" : "forward",
                    "TargetGroupArn" : { "Ref" : KW['TargetGroupArn'] }
                }],
                "LoadBalancerArn": { "Ref": KW['LoadBalancerArn'] },
                "Port" : 80,
                "Protocol" : "HTTP"
                #"Port": 443,
                #"Protocol": "HTTPS",
                #"SslPolicy" : "ELBSecurityPolicy-TLS-1-2-Ext-2018-06"
            },
            "DependsOn" : [
                KW['TargetGroupArn'],
                KW['LoadBalancerArn']
            ]
        }
    elif type == 'elbv2listenerredirect':
        check(KW,'LoadBalancerArn')
        return {
            "Type": "AWS::ElasticLoadBalancingV2::Listener",
            "Properties": {
                "DefaultActions": [
                    {
                        "Type": "redirect",
                        "RedirectConfig": {
                            "Protocol": "HTTPS",
                            "Port": 443,
                            "Host": "#{host}",
                            "Path": "/#{path}",
                            "Query": "#{query}",
                            "StatusCode": "HTTP_301"
                        }
                    }
                ],
                "LoadBalancerArn": { "Ref": KW['LoadBalancerArn'] },
                "Port" : 80,
                "Protocol" : "HTTP"
                #"Port": 443,
                #"Protocol": "HTTPS",
                #"SslPolicy" : "ELBSecurityPolicy-TLS-1-2-Ext-2018-06"
            },
            "DependsOn" : [
                KW['LoadBalancerArn']
            ]
        }
    elif type == 'dynamodb':
        return {
            "Type" : "AWS::DynamoDB::Table",
            "Properties" : {
                "AttributeDefinitions" : [ {'AttributeName': 'id', 'AttributeType': 'S'} ],
                "KeySchema" : [ {'AttributeName': 'id', 'KeyType': 'HASH'} ],
                "ProvisionedThroughput" : {
                    "ReadCapacityUnits" : "5",
                    "WriteCapacityUnits" : "5"
                },
                "TableName" : name,
                "Tags" : [{
                    "Key" : "Name",
                    "Value" : name
                }],
            }
        }
    elif type == 'policydynamodb':
        check(KW,'TableName')

        return {
            "Effect" : "Allow",
            "Action" : [
                "dynamodb:DeleteItem",
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:UpdateItem"
            ],
            "Resource": { "Fn::Join": [ "", [ "arn:" , { "Ref" : "AWS::Partition"} , ":dynamodb:" , { "Ref" : "AWS::Region"} , ":" , { "Ref" : "AWS::AccountId"} , ":table/", { "Ref" : KW['TableName'] } ] ] }
        }
    elif type == 'policys3bucket':
        check(KW,'Bucket')

        return {
            "Effect" : "Allow",
            "Action" : [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBuckets"
            ],

            "Resource": { "Fn::Join": [ "", [ "arn:" , { "Ref" : "AWS::Partition"} , ":s3:::", { "Ref" : KW['Bucket'] }, "/*" ] ] },
        }
    elif type == 'policyssmparameter':
        check(KW,'parameter')
        return {
            "Effect" : "Allow",
            "Action" : [
                "ssm:GetParameter",
            ],
            "Resource" : [
                { "Fn::Sub": "arn:${AWS::Partition}:ssm:${AWS::Region}:${AWS::AccountId}:parameter/" + KW['parameter'] }
            ]
        }
    elif type == 'outputfnatt':
        check(KW,'attribute')
        check(KW,'description')
        return {
            "Value" : { "Fn::GetAtt" : [ name, KW['attribute'] ] },
            "Description": KW['description']
        }
    elif type == 'parameterlatestamiid':
        return {
            "Type" : "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
            "Default" : "/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2",
            "Description" : "Path to the SSM Parameter that contains the latest Amazon Linux 2 image ID"
        }
    elif type == 'parameter':
        check(KW,'Type')
        check(KW,'description')
        if not 'NoEcho' in KW:
            KW['NoEcho'] = False

        return {
            "Type" : KW['Type'],
            "Description" : KW['description'],
            "NoEcho"        : KW['NoEcho']
        }
    else:
        log("FATAL",f"Unknown resource type - {type}")
   
   
# =========================== Other code procedures ===========================

def log(e,t):
    if e != '':
        print(f"[{e}] {t}")
    else:
        print("---------------------------------------")
        print(f"{t}")
        print("---------------------------------------")

    if e == "FATAL":
        #input()
        exit(1)

def findResources(cf,res):
    l = []
    for r in cf['Resources']:
        if cf['Resources'][r]['Type'] == res:
            l.append(r)
    return l

def resourceSelector(cf,cmdline,resourcetype,id = None,param = None):
    # == did we specify something on the command line?
    
    if cmdline:
        # == does it not exist?  Fail
        items = []
        if param != None and param.startswith('List') and ',' in cmdline:
            itms = cmdline.split(',')
        else:
            itms = [ cmdline ]

        for i in itms:
            if not i in cf['Resources']:
                log("FATAL",f"Unknown resource specified - {i}")
            else:
                if not cf['Resources'][i]['Type'] == resourcetype:
                    log("FATAL",f"Resource {cmdline} is not a type {resourcetype}")
                
        log("INFO",f"selected {resourcetype} -> {cmdline}")
        if id in cf['Parameters']:
            log("WARNING",f"Deleting Parameter {id}")
            del cf['Parameters'][id]

        return cmdline
    else:
        x = findResources(cf,resourcetype)
        if len(x) == 0:
            if id != None:
                log("WARNING",f"Creating Parameter for {id} ({param})")
                cf['Parameters'][id] = { "Type" : param } 
                return id
            else:
                log("FATAL",f"No resource of type {resourcetype} exists.")
        elif len(x) == 1:
            log("INFO",f"assumed {resourcetype} -> {x[0]}")
            return x[0]
        else:
            log("ERROR",f"No {resourcetype} was specified, and we cannot assume what to use.")
            for y in x:
                log("INFO",f" - {y}")
            log("FATAL","Cannot assume a single resource to use")

def securityGroupRule(cf,cidr,tcp,udp):
    
    if tcp and udp:
        log("FATAL","Do not specify both TCP and UDP.  Do them one at a time.")

    # == start building a rule
    rule = { "IpProtocol" : "-1" }
    if tcp != None and udp == None:
        rule = { "IpProtocol" : "tcp", "FromPort" : tcp, "ToPort" : tcp }
    if tcp == None and udp != None:
        rule = { "IpProtocol" : "udp", "FromPort" : udp, "ToPort" : udp }

    # == is this a IPv4 CIDR?
    if re.match("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\/\d{1,2}$",cidr):
        rule['CidrIp'] = cidr
    else:
        # -- check if the reference provided is a security group
        if cidr not in cf['Resources']:
            log("FATAL",f"Not a resource in the CloudFormation template - {cidr}")
        else:
            
            if not cf['Resources'][cidr]['Type'] == 'AWS::EC2::SecurityGroup':
                log("FATAL","You can only link a security group to another security group.")

            rule['SourceSecurityGroupId'] = { "Ref" : cidr }

    log('INFO',' - Adding security group rule')
    return rule

def main():
    parser = argparse.ArgumentParser(description='CloudFormation Helper')
    parser.add_argument('-cf', help='Path to the CloudFormation json file', required=True)
    parser.add_argument('-add',help='Add a new resource to the CloudFormation file',nargs='+')
    parser.add_argument('-properties',help='Add a custom Properties value into the resource',nargs='+')
    parser.add_argument('-list',help='List the resources',action='store_true')
    parser.add_argument('-overwrite',help='Overwrite a resource',action='store_true')
    parser.add_argument('-link',help='Links one resource to another',nargs='+')
    parser.add_argument('-desc',help='Set a description for the CloudFormation file')
    parser.add_argument('-sg',help='Specify a security group resource to use - if none is specified, a parameter will be used')
    parser.add_argument('-lt',help='Specify a launch template to use if there are more than 1 created (used by autoscaling).')
    parser.add_argument('-cron',help='Specify a cron schedule (used by eventbridge')
    parser.add_argument('-target',help='Specify a lambda function (used by eventbridge')
    parser.add_argument('-vpc',help='Specify the VPC id to use (used by natgateway)')
    parser.add_argument('-cidr',help='Specify the CIDR range to use (used by vpc and subnet)')
    parser.add_argument('-routetable',help='Specify the route table to use (used by publicsubnet and privatesubnet)')
    parser.add_argument('-az',help='Specify the availability zone to use (0,1,2) (used by publicsubnet and privatesubnet)')
    parser.add_argument('-subnet',help='Specify a subnet to use')
    parser.add_argument('-ingress',help='Specify the ingress CIDR range or resource to link to a security group')
    parser.add_argument('-egress',help='Specify the egress CIDR range or resource to link to a security group')
    parser.add_argument('-tcp',help='Specify the TCP port to link to a security group')
    parser.add_argument('-udp',help='Specify the TCP port to link to a security group')
    parser.add_argument('-value',help='Specify a value for an SSM Parameter')

    parser.add_argument('-updatestack',help='Update the CloudFormation stack (specify the stack name)')
    
    args = parser.parse_args()

    # == go get the CF file, and if it doesn't exist, create it
    if not os.path.exists(args.cf):
        log("WARNING",f"CloudFormation File {args.cf} does not exist..")
        cloudFormation = {}
    else:
        log("INFO",f"Reading CloudFormation File {args.cf}...")
        with open(args.cf,'rt') as a:
            cloudFormation = json.load(a)

    # -- set the Description, if the user wanted it to
    if args.desc:
        cloudFormation['Description'] = args.desc

    # == do a QA on the file -- some things just have to exist in it.  If it doesn't, put it in
    if not 'AWSTemplateFormatVersion' in cloudFormation:
        log("INFO","Setting default AWSTemplateFormatVersion")
        cloudFormation['AWSTemplateFormatVersion'] = '2010-09-09'
    if not 'Description' in cloudFormation:
        log("INFO","Setting default Description")
        cloudFormation['Description'] = "CloudFormation Helper Script"
    for x in ['Parameters','Resources','Outputs']:
        if not x in cloudFormation:
            log("WARNING",f"Creating a blank {x} leaf")
            cloudFormation[x] = {}

    # == list resources
    if args.list:
        for r in cloudFormation['Resources']:
            t = cloudFormation['Resources'][r]['Type']
            print(f"{t} - {r}")
        exit(0)

    # == add resources to the file
    if args.add:
        if len(args.add) != 2:
            log("FATAL","When you call -add, you must use the format -add <type> <name>")
        
        resource = args.add[0]

        # -- the name must only be alpha numeric
        name = ''.join(c for c in args.add[1] if c.isalnum())
        if name != args.add[1]:
            log("WARNING",f"Resource name {name} has been adjusted to meet CloudFormation requirements.  See \"Logical Id\" in https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resources-section-structure.html for more information")

        # TODO - we need to figure out how we deal with security groups.. They're a little tricky with the -overwrite option
        #if name in cloudFormation['Resources'] and not args.overwrite:
        #    log("FATAL",f"Cannot add resource {name} - it already exists.  Use -overwrite to replace it.")

        log("",f"Adding resources type {resource} - {name}")

        if resource == 'vpc':
            cloudFormation['Resources'][name] = resourceTemplate(name,'vpc',cidr = args.cidr)
            cloudFormation['Resources'][f"{name}InternetGateway"] = resourceTemplate(f"{name}InternetGateway",'igw')
            cloudFormation['Resources'][f"{name}InternetGatewayAttachment"] = resourceTemplate(f"{name}InternetGatewayAttachment","igwattachment",vpc = name, InternetGatewayId = f"{name}InternetGateway")
            cloudFormation['Resources'][f"{name}RouteTableInternetGateway"] = resourceTemplate(f"{name}RouteTableInternetGateway","routetable",vpc = name)
            cloudFormation['Resources'][f"{name}RouteInternetGateway"] = resourceTemplate(f"{name}RouteInternetGateway","routeigw",InternetGatewayId = f"{name}InternetGateway",RouteTableId = f"{name}RouteTableInternetGateway")       
        elif resource == 'publicsubnet':
            vpc = resourceSelector(cloudFormation,args.vpc,"AWS::EC2::VPC")
            RouteTable = resourceSelector(cloudFormation,args.routetable,"AWS::EC2::RouteTable")
            cloudFormation['Resources'][f"{name}"] = resourceTemplate(name,"subnet",vpc = vpc, cidr = args.cidr, az = args.az,MapPublicIpOnLaunch = True )
            cloudFormation['Resources'][f"{name}Route"] = resourceTemplate(f"{name}Route","subnetroute",RouteTableId = RouteTable, SubnetId = name)     
        elif resource == 'privatesubnet':
            vpc = resourceSelector(cloudFormation,args.vpc,"AWS::EC2::VPC")
            RouteTable = resourceSelector(cloudFormation,args.routetable,"AWS::EC2::RouteTable")
            cloudFormation['Resources'][f"{name}"] = resourceTemplate(name,"subnet",vpc = vpc, cidr = args.cidr, az = args.az,MapPublicIpOnLaunch = False )
            cloudFormation['Resources'][f"{name}Route"] = resourceTemplate(f"{name}Route","subnetroute",RouteTableId = RouteTable, SubnetId = name)
        elif resource == 'securitygroup':
            vpc = resourceSelector(cloudFormation,args.vpc,"AWS::EC2::VPC","VpcId","AWS::EC2::VPC::Id")
            if not name in cloudFormation['Resources']:
                cloudFormation['Resources'][name] = resourceTemplate(name,'securitygroup',vpc = vpc)

            if args.ingress:
                cloudFormation['Resources'][name]['Properties']['SecurityGroupIngress'].append(
                    securityGroupRule(cloudFormation,args.ingress,args.tcp,args.udp)
                )
            if args.egress:
                cloudFormation['Resources'][name]['Properties']['SecurityGroupEgress'].append(
                    securityGroupRule(cloudFormation,args.egress,args.tcp,args.udp)
                )
        elif resource == 's3':
            cloudFormation['Resources'][name] = resourceTemplate(name,'s3')
        elif resource == 'ec2':
            subnet = resourceSelector(cloudFormation,args.subnet,"AWS::EC2::Subnet",f"{name}Subnet","AWS::EC2::Subnet::Id")
            mySG = resourceSelector(cloudFormation,args.sg,"AWS::EC2::SecurityGroup",f"{name}SecurityGroup","AWS::EC2::SecurityGroup::Id")
            
            cloudFormation['Parameters']['LatestAmiId'] = resourceTemplate(None,'parameterlatestamiid')
            cloudFormation['Resources'][f"{name}ec2Role"] = resourceTemplate(f"{name}ec2Role","ec2role")
            cloudFormation['Resources'][f"{name}ec2InstanceProfile"] = resourceTemplate(f"{name}ec2InstanceProfile","instanceprofile",Role = f"{name}ec2Role")
            cloudFormation['Resources'][name] = resourceTemplate(name,'ec2instance',IamInstanceProfile = f"{name}ec2InstanceProfile", ImageId = 'LatestAmiId',SecurityGroup = mySG,Subnet = subnet)
        elif resource == 'static':
            cloudFormation['Resources'][name] = resourceTemplate(name,'static')
            cloudFormation['Resources'][f"{name}bucketPolicy"] = resourceTemplate(f"{name}bucketPolicy",'staticbucketpolicy',Bucket = name)
            cloudFormation['Outputs'][name] = resourceTemplate(name,'outputfnatt',attribute = 'WebsiteURL', description = "URL for website hosted on S3" )              
        elif resource == 'natgateway':
            subnet = resourceSelector(cloudFormation,args.subnet,"AWS::EC2::Subnet")
            vpc = resourceSelector(cloudFormation,args.vpc,"AWS::EC2::VPC")
            
            cloudFormation['Resources'][f"{name}ElasticIP"] = resourceTemplate(f"{name}ElasticIP",'eip')
            cloudFormation['Resources'][name] = resourceTemplate(name,"natgateway",subnet = subnet, eip = f"{name}ElasticIP")
            cloudFormation['Resources'][f"{name}RouteTableNATGateway"] = resourceTemplate(f"{name}RouteTableNATGateway","routetable",vpc = vpc)
            cloudFormation['Resources'][f"{name}RouteNATGateway"] = resourceTemplate(f"{name}RouteNATGateway","routenatgw", NatGatewayId = name, RouteTableId = f"{name}RouteTableNATGateway")      
        elif resource == 'lambda':
            cloudFormation['Resources'][name] = resourceTemplate(name,'lambda',Role = f"{name}ExecutionRole")
            cloudFormation['Resources'][f"{name}ExecutionRole"] = resourceTemplate(f"{name}ExecutionRole","lambdaexecutionrole")
        elif resource == 'launchtemplate':
            mySG = resourceSelector(cloudFormation,args.sg,"AWS::EC2::SecurityGroup",f"{name}SecurityGroup","AWS::EC2::SecurityGroup::Id")
            cloudFormation['Parameters']['LatestAmiId'] = resourceTemplate(None,'parameterlatestamiid')
            cloudFormation['Resources'][f"{name}ec2Role"] = resourceTemplate(f"{name}ec2Role","ec2role")
            cloudFormation['Resources'][f"{name}ec2InstanceProfile"] = resourceTemplate(f"{name}ec2InstanceProfile","instanceprofile",Role = f"{name}ec2Role")
            cloudFormation['Resources'][f"{name}"] = resourceTemplate(name,'launchtemplate',IamInstanceProfile = f"{name}ec2InstanceProfile", ImageId = "LatestAmiId", SecurityGroup = mySG)
        elif resource == 'autoscaling':
            vpc = resourceSelector(cloudFormation,args.vpc,"AWS::EC2::VPC","VpcId","AWS::EC2::VPC::Id")
            subnets = resourceSelector(cloudFormation,args.subnet,'AWS::EC2::Subnet',f"{name}Subnets","List<AWS::EC2::Subnet::Id>").split(',')
            lt = resourceSelector(cloudFormation,args.lt,'AWS::EC2::LaunchTemplate')
            VPCZoneIdentifier = []
            for x in subnets:
                VPCZoneIdentifier.append({"Ref" : x })
            cloudFormation['Resources'][f"{name}TargetGroup"] = resourceTemplate(name,'targetgroup',vpc = vpc)
            cloudFormation['Resources'][f"{name}AutoScaling"] = resourceTemplate(f"{name}AutoScaling",'autoscaling',VPCZoneIdentifier = VPCZoneIdentifier, LaunchTemplateId = lt, TargetGroupARNs = f"{name}TargetGroup")          
        elif resource == 'elbv2':
            mySG = resourceSelector(cloudFormation,args.sg,"AWS::EC2::SecurityGroup",f"{name}SecurityGroup","AWS::EC2::SecurityGroup::Id")
            subnets = resourceSelector(cloudFormation,args.subnet,'AWS::EC2::Subnet',f"{name}Subnets","List<AWS::EC2::Subnet::Id>").split(',')
            target = resourceSelector(cloudFormation,args.target,"AWS::ElasticLoadBalancingV2::TargetGroup")

            cloudFormation['Resources'][name] = resourceTemplate(name,'elbv2',SecurityGroups = mySG, subnet = subnets)
            cloudFormation['Resources'][f"{name}Listener"] = resourceTemplate(f"{name}Listener",'elbv2listener', LoadBalancerArn = name,TargetGroupArn = target)
            
            cloudFormation['Outputs'][name] = resourceTemplate(name,'outputfnatt',attribute = 'DNSName', description = "URL for application load balancer" )
        elif resource == 'parameter':
            cloudFormation['Parameters'][name] = resourceTemplate(name,'parameter', description = name, Type = "String")
        elif resource == 'eventbridge':
            # -- confirm that target actually exists
            if cloudFormation['Resources'].get(args.target,{}).get('Type','') == "AWS::Lambda::Function":
                cloudFormation['Resources'][name] = resourceTemplate(name,'eventbridgeschedule',cron = args.cron, target = args.target)
                cloudFormation['Resources'][f"{name}lambdaPermission"] = resourceTemplate(f"{name}lambdaPermission","lambdaeventbridgepermission",target = args.target, eventbridge = name)
            else:
                log("FATAL","event bridge -target does not exist or is not a Lambda function")
        elif resource == 'functionurl':
            cloudFormation['Resources'][name] = resourceTemplate(name,'functionurl',target = args.target)
            cloudFormation['Resources'][f"{name}permission"] = resourceTemplate(f"{name}permission","lambdafunctionurlpublicpermission",target = name)
            cloudFormation['Outputs'][name] = {
                "Value" : { "Fn::GetAtt" : [ name, "FunctionUrl" ] },
                "Description": "URL for Lambda function"
            }
        elif resource == 'ssmparameter':
            cloudFormation['Resources'][name] = resourceTemplate(name,'ssmparameter',value = args.value)
        elif resource == 'rds':
            cloudFormation['Parameters'][f"{name}MasterUsername"] = resourceTemplate(f"{name}MasterUsername",'parameter', description = f"{name}MasterUsername", Type = "String")
            cloudFormation['Parameters'][f"{name}MasterUserPassword"] = resourceTemplate(f"{name}MasterUserPassword",'parameter', description = f"{name}MasterUserPassword", Type = "String", NoEcho = True)

            subnets = resourceSelector(cloudFormation,args.subnet,'AWS::EC2::Subnet',f"{name}Subnets","List<AWS::EC2::Subnet::Id>").split(',')
            mySG = resourceSelector(cloudFormation,args.sg,"AWS::EC2::SecurityGroup",f"{name}SecurityGroup","AWS::EC2::SecurityGroup::Id")

            cloudFormation['Resources'][name] = resourceTemplate(name,'rds',MasterUsername = f"{name}MasterUsername",MasterUserPassword = f"{name}MasterUserPassword", sg = mySG, DBSubnetGroupName = f"{name}SubnetGroup")
            cloudFormation['Resources'][f"{name}SubnetGroup"] = resourceTemplate(f"{name}SubnetGroup",'dbsubnetgroup',DBSubnetGroupDescription = name, subnet = subnets)

            cloudFormation['Outputs'][name] = {
                "Value" : { "Fn::GetAtt" : [ name, "Endpoint.Address" ] },
                "Description": "Database Endpoint"
            }
        elif resource == 'dynamodb':
            cloudFormation['Resources'][name] = resourceTemplate(name,'dynamodb')
        else:
            log("FATAL",f"Unknown resource type - {resource}")
            
    # == Add properties
    if args.properties:
        name = args.properties[0]
        KEY = args.properties[1]
        VALUE = args.properties[2]

        if not name in cloudFormation['Resources']:
            log("FATAL","Unable to update Properties - resource {name} does not exist.")

        log("WARNING",f"Updating properties for {name}.{KEY} = {VALUE}")
        cloudFormation['Resources'][name]['Properties'][KEY] = VALUE
        
    # == Update the code for all Lambda function
    for name in cloudFormation['Resources']:
        if cloudFormation['Resources'][name]['Type'] == 'AWS::Lambda::Function':
            log("INFO",f"Lambda code update for {name}")
            if os.path.exists(f"{name}.py"):
                log("INFO",f" - Found {name}.py - Updating")
                # TODO - if the file is too big, Lambda will not update it
                pc = []
                with open(f"{name}.py",'rt') as C:
                    for x in C.readlines():
                        pc.append(x.replace('\n',''))
                    cloudFormation['Resources'][name]['Properties']['Code']['ZipFile'] =  { "Fn::Join": ["\n", pc ]}
            else:
                log("WARNING",f' - Create a file called {name}.py to cause cfh to update the code automatically')

    # == Update EC2 Launch Template UserData
    for name in cloudFormation['Resources']:
        if os.path.exists(f"{name}.sh"):
            pc = []
            with open(f"{name}.sh",'rt') as C:
                for x in C.readlines():
                    pc.append(x.replace('\n',''))

            if cloudFormation['Resources'][name]['Type'] == 'AWS::EC2::LaunchTemplate':
                log("INFO",f"Found {name}.sh - Updating Launch Template User Data {name}")
                cloudFormation['Resources'][name]['Properties']['LaunchTemplateData']['UserData'] = { "Fn::Base64": {"Fn::Join": [ "\n", pc ] } }
            if cloudFormation['Resources'][name]['Type'] == 'AWS::EC2::Instance':
                log("INFO",f"Found {name}.sh - Updating EC2 User Data {name}")
                cloudFormation['Resources'][name]['Properties']['UserData'] = { "Fn::Base64": {"Fn::Join": [ "\n", pc ] } }

    # == link resources to each other
    if args.link:
        if not args.link[0] in cloudFormation['Parameters'] and not args.link[0] in cloudFormation['Resources']:
            log("FATAL",f"Cannot link {args.link[0]} - it does not exist")
        if not args.link[1] in cloudFormation['Resources']:
            log("FATAL",f"Cannot link {args.link[1]} - it does not exist")

        if args.link[0] in cloudFormation['Parameters'] and args.link[1] in cloudFormation['Resources']:
            if cloudFormation['Resources'][args.link[1]]['Type'] == 'AWS::Lambda::Function':
                log("INFO",f"Linking Parameter ({args.link[0]}) to Lambda ({args.link[1]})")
                cloudFormation['Resources'][args.link[1]]['Properties']['Environment']['Variables'][args.link[0]] = { "Ref" : args.link[0] } 

        if args.link[0] in cloudFormation['Resources'] and args.link[1] in cloudFormation['Resources']:
            # -- linking s3 to ec2
            if cloudFormation['Resources'][args.link[0]]['Type'] == 'AWS::S3::Bucket' and cloudFormation['Resources'][args.link[1]]['Type'] == 'AWS::EC2::Instance':
                log("INFO",f"Linking S3 ({args.link[0]}) to EC2 Role ({args.link[1]})")
                x = cloudFormation['Resources'][f"{args.link[1]}ec2Role"]['Properties']['AssumeRolePolicyDocument']['Statement']
                
                p = resourceTemplate(None, 'policys3bucket', Bucket = args.link[0])
                
                if not p in x:
                    log("WARNING","Updating policy")
                    x.append(p)
                else:
                    log("INFO","Policy unchanged")

            # -- linking x to lambda
            if cloudFormation['Resources'][args.link[1]]['Type'] == 'AWS::Lambda::Function':
                
                # -- find the Lambda execution policy
                ExecutionRole = cloudFormation['Resources'][args.link[1]]['Properties']['Role']['Fn::GetAtt'][0]
                # -- update the Lambda Execution Role policy
                x = cloudFormation['Resources'][ExecutionRole]['Properties']['Policies'][0]['PolicyDocument']['Statement']

                if cloudFormation['Resources'][args.link[0]]['Type'] == 'AWS::DynamoDB::Table':
                    log("INFO",f"Linking DynamoDb ({args.link[0]}) to Lambda ({args.link[1]})")
                    p = resourceTemplate(None, 'policydynamodb', TableName = args.link[0])

                if cloudFormation['Resources'][args.link[0]]['Type'] == 'AWS::S3::Bucket':
                    log("INFO",f"Linking S3 ({args.link[0]}) to Lambda ({args.link[1]})")
                    p = resourceTemplate(None, 'policys3bucket', Bucket = args.link[0])

                if cloudFormation['Resources'][args.link[0]]['Type'] == 'AWS::SSM::Parameter':
                    log("INFO",f"Linking SSM Parameter ({args.link[0]}) to Lambda ({args.link[1]})")
                    p = resourceTemplate(None, 'policyssmparameter', parameter = args.link[0])

                if not p in x:
                    log("WARNING","Updating policy")
                    x.append(p)
                else:
                    log("INFO","Policy unchanged")
                
                # -- update the Lambda variable
                cloudFormation['Resources'][args.link[1]]['Properties']['Environment']['Variables'][args.link[0]] = { "Ref" : args.link[0] } 

                # -- Add it into the DependsOn (if it's not already there)
                if args.link[0] not in cloudFormation['Resources'][args.link[1]]['DependsOn']:
                    cloudFormation['Resources'][args.link[1]]['DependsOn'].append(args.link[0])

            #else:
                #log("FATAL","Unsupported linking direction")

        
    #print(json.dumps(cloudFormation, indent=4))

    log("INFO",f"Writing {args.cf}")
    result = json.dumps(cloudFormation,indent=4)
    with open(args.cf,"wt") as Q:
        Q.write(result)

    if args.updatestack:
        Parameters = []
        for ParameterKey in cloudFormation['Parameters']:
            Parameters.append({
                "ParameterKey" : ParameterKey,
                "UsePreviousValue" : True
            })
        
        log("WARNING","====================================================================")
        log("WARNING",f"UPDATING CLOUDFORMATION STACK - {args.updatestack}")
        response = boto3.client('cloudformation').update_stack(  
            StackName = args.updatestack,
            TemplateBody = result,  
            Capabilities = ['CAPABILITY_IAM'],
            Parameters = Parameters
        )
        if 'StackId' in response:
            log("INFO",response['StackId'])
        else:
            print(response)
        log("WARNING","====================================================================")

if __name__ == '__main__':
    main()

