import json
from re import M
import sys
import os
import argparse

# =========================== Parameter Templates ===========================

def parameter_LatestAmiId():
    return {
        "Type" : "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
        "Default" : "/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2",
        "Description" : "Path to the SSM Parameter that contains the latest Amazon Linux 2 image ID"
    }

def parameter_SecurityGroup():
    return {
        "Type" : "AWS::EC2::SecurityGroup::Id",
        "Description" : "Select a security group"
    }

def parameter_Subnets():
    return {
        "Type": "List<AWS::EC2::Subnet::Id>"
    }

def parameter_Subnet():
    return {
        "Type": "AWS::EC2::Subnet::Id"
    }

def parameter_vpc():
    return {
        "Type" : "AWS::EC2::VPC::Id"
    }

# =========================== Resource Templates ===========================

def resource_autoscaling(name,lt,VPCZoneIdentifier):
    return {
        "Type" : "AWS::AutoScaling::AutoScalingGroup",
        "Properties" : {
            "AutoScalingGroupName" : name,
            "DesiredCapacity"   : 1,
            "LaunchTemplate" : {
                "LaunchTemplateId" : { "Ref" : lt },
                "Version" : { "Fn::GetAtt": [ lt, "LatestVersionNumber" ] }
            },
            "VPCZoneIdentifier" : VPCZoneIdentifier,
            "MaxSize" : 1,
            "MinSize" : 1
        },
        "DependsOn" : [ lt ]
    }

def resource_ec2Role():
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

def resource_ec2Instance(IamInstanceProfile,ImageId,SecurityGroup, Subnet):
    return {
        "Type" : "AWS::EC2::Instance",
        "Properties" : {
            "ImageId" : { "Ref" : ImageId },
            "IamInstanceProfile"    : { "Ref" : IamInstanceProfile },
            "InstanceType" : "t2.micro",
            "NetworkInterfaces": [ {
                "AssociatePublicIpAddress": "true",
                "DeviceIndex": "0",
                "GroupSet": [{ "Ref" : SecurityGroup }],
                "SubnetId": { "Ref" : Subnet }
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
            "UserData"              : { "Fn::Base64" : { "Fn::Join" : ["\n", [
                    "#!/usr/bin/bash",
                    "yum update -y"
                ]]}},
        },
        "DependsOn" : [
            SecurityGroup,
            IamInstanceProfile
        ]
    }

def resource_ec2InstanceProfile(role):
    return {
        "Type": "AWS::IAM::InstanceProfile",
        "Properties": {
            "Path": "/",
            "Roles": [ { "Ref": role } ]
        },
        "DependsOn" : [ role ]
    }

def resource_ec2LaunchTemplate(name,IamInstanceProfile,ImageId,SecurityGroup):
    return {
        "Type":"AWS::EC2::LaunchTemplate",
        "Properties":{
            "LaunchTemplateName":name,
            "LaunchTemplateData":{
                "IamInstanceProfile":{ "Arn":{"Fn::GetAtt": [IamInstanceProfile, "Arn"]} },
                "DisableApiTermination":"true",
                "ImageId": { "Ref" : ImageId },
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
                "SecurityGroupIds" : [ { "Ref" : SecurityGroup } ]
            }
        },
        "DependsOn" : [
            IamInstanceProfile
        ]
    }

def resource_lambda(name):
    return {
        "Type": "AWS::Lambda::Function",
        "Properties": {
            "Handler": "index.lambda_handler",
            "Role": { "Fn::GetAtt": [ f"{name}ExecutionRole", "Arn" ] },
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
        "DependsOn" : [ f"{name}ExecutionRole" ]
    }

def resource_lambda_ExecutionRole(name):
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

def resource_s3():
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

def resource_securitygroup_web(vpc):
    return {
        "Type": "AWS::EC2::SecurityGroup",
        "Properties": {
            "GroupDescription": "Enable HTTP access via port 80 and 443, and all outgoing traffic",
            "SecurityGroupIngress" : [
                { "IpProtocol" : "tcp", "FromPort" : 80, "ToPort" : 80, "CidrIp" : "0.0.0.0/0" },
                { "IpProtocol" : "tcp", "FromPort" : 443, "ToPort" : 443, "CidrIp" : "0.0.0.0/0" }
            ],
            "SecurityGroupEgress" : [
                { "IpProtocol" : "-1", "CidrIp" : "0.0.0.0/0" }
            ],
            "VpcId": { "Ref": vpc}
        }
    }

def resource_static():
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

def resource_static_bucketPolicy(name):
    return {
        "Type": "AWS::S3::BucketPolicy",
        "Properties": {
            "Bucket": { "Ref" : name},
            "PolicyDocument": {
                "Version": "2012-10-17",
                "Statement": {
                    "Effect": "Allow",
                    "Principal": "*",
                    "Action": "s3:GetObject",
                    "Resource": { "Fn::Join": [ "", [ "arn:aws:s3:::", { "Ref": name }, "/*" ] ] },
                }
            }
        },
        "DependsOn" : [ name ]
    }

def resource_vpc(cidr):
    return  {
        "Type" : "AWS::EC2::VPC",
        "Properties" : {
            "CidrBlock" : cidr,
            "EnableDnsHostnames" : True,
            "EnableDnsSupport" : True,
            "InstanceTenancy" : "default"
        }
    }

def resource_vpc_subnet(vpc,cidr,az,extra):
    v = {
        "Type" : "AWS::EC2::Subnet",
        "Properties" : {
            "VpcId" : { "Ref" : vpc },
            "CidrBlock" : cidr,
            "AvailabilityZone" : {
            "Fn::Select" : [ 
                az, 
                { 
                "Fn::GetAZs" : "" 
                } 
            ]
            }
        }
    }

    for x in extra:
        v['Properties'][x] = extra[x]
    return v

def resource_vpc_igw():
    return {
        "Type" : "AWS::EC2::InternetGateway",
        "Properties" : {}
    }

def resource_vpc_igw_attachment(igw,vpc):
    return {
        "Type" : "AWS::EC2::VPCGatewayAttachment",
        "Properties" : {
            "InternetGatewayId" : { "Ref" : igw },
            "VpcId" : { "Ref" : vpc }
        },
    "DependsOn" : [ igw, vpc ],
    }

def resource_vpc_route_table(vpc):
    return {
        "Type" : "AWS::EC2::RouteTable",
        "Properties" : {
            "VpcId" : { "Ref" : vpc }
        },
        "DependsOn" : [ vpc ]
    }

def resource_vpc_default_route_igw(igw,routeTable):
    return {
        "Type" : "AWS::EC2::Route",
        "Properties" : {
            "RouteTableId" : { "Ref" :  routeTable  },
            "DestinationCidrBlock" : "0.0.0.0/0",
            "GatewayId" : { "Ref" : igw }
        },
        "DependsOn" : [ igw, routeTable ]
    }

def resource_vpc_subnet_route(subnet,route):
    return {
        "Type" : "AWS::EC2::SubnetRouteTableAssociation",
        "Properties" : {
            "RouteTableId" : { "Ref" : route },
            "SubnetId" : { "Ref" : subnet }
        },
        "DependsOn" : [ route, subnet]
    }

# =========================== Output Templates ===========================

def output_WebsiteURL(name):
    return {
        "Value" : { "Fn::GetAtt" : [ name, "WebsiteURL" ] },
        "Description": "URL for website hosted on S3"
    }

# =========================== Other code procedures ===========================

def request_sg(name,cloudFormation,args):
    if args.sg:
        if not args.sg in cloudFormation['Resources']:
            for r in cloudFormation['Resources']:
                if cloudFormation['Resources'][r]['Type'] == 'AWS::EC2::SecurityGroup':
                    log("INFO",f" - Found Security Group : {r}")

            log("FATAL","A security group was specified that does not exist in the template")
        else:
            if not cloudFormation['Resources'][args.sg]['Type'] == 'AWS::EC2::SecurityGroup':
                log("FATAL","A CloudFormation resource was provided that is not a Security Group")

        if f'{name}SecurityGroup' in cloudFormation['Parameters']:
            log("WARNING",f"Removing parameter - {name}SecurityGroup")
            del cloudFormation['Parameters'][f'{name}SecurityGroup']
        return args.sg

    else:
        log("INFO","Creating a parameter for request the security group name")
        cloudFormation['Parameters'][f'{name}SecurityGroup'] = parameter_SecurityGroup()
        return f'{name}SecurityGroup'

    return None

def log(e,t):
    print(f"[{e}] - {t}")
    if e == "FATAL":
        exit(1)

def findResources(cf,res):
    l = []
    for r in cf['Resources']:
        if cf['Resources'][r]['Type'] == res:
            l.append(r)
    return l

def main():
    parser = argparse.ArgumentParser(description='CloudFormation Helper')
    parser.add_argument('-cf', help='Path to the CloudFormation json file', required=True)
    parser.add_argument('-add',help='Add a new resource to the CloudFormation file',nargs='+')
    parser.add_argument('-list',help='List the resources',action='store_true')
    parser.add_argument('-link',help='Links one resource to another',nargs='+')
    parser.add_argument('-desc',help='Set a description for the CloudFormation file')
    parser.add_argument('-sg',help='Specify a security group resource to use - if none is specified, a parameter will be used')
    parser.add_argument('-lt',help='Specify a launch template to use if there are more than 1 created (used by autoscaling).')
    parser.add_argument('-subnet',help='Specify a subnet to use')
    
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
        resource = args.add[0]

        # -- the name must only be alpha numeric
        name = ''.join(c for c in args.add[1] if c.isalnum())
        if name != args.add[1]:
            log("WARNING",f"Resource name {name} has been adjusted to meet CloudFormation requirements.  See \"Logical Id\" in https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/resources-section-structure.html for more information")

        log("INFO",f"Adding resources type {resource} - {name}")

        if resource == 's3':
            cloudFormation['Resources'][name] = resource_s3()
        elif resource == 'static':
            cloudFormation['Resources'][name] = resource_static()
            cloudFormation['Resources'][f"{name}bucketPolicy"] = resource_static_bucketPolicy(name)
            cloudFormation['Outputs'][name] = output_WebsiteURL(name)
        elif resource == 'lambda':
            cloudFormation['Resources'][name] = resource_lambda(name)
            cloudFormation['Resources'][f"{name}ExecutionRole"] = resource_lambda_ExecutionRole(name)
            log("INFO",f'Create a file called {name}.py to cause cfh to update the code automatically')
        elif resource == 'launchtemplate':
            mySG = request_sg(name,cloudFormation,args)
            cloudFormation['Parameters']['LatestAmiId'] = parameter_LatestAmiId()
            cloudFormation['Resources'][f"{name}ec2Role"] = resource_ec2Role()
            cloudFormation['Resources'][f"{name}ec2InstanceProfile"] = resource_ec2InstanceProfile(f"{name}ec2Role")
            cloudFormation['Resources'][f"{name}"] = resource_ec2LaunchTemplate(name,f"{name}ec2InstanceProfile","LatestAmiId",mySG)
        elif resource == 'autoscaling':
            if args.subnet:
                subnet = args.subnet.split(',')
                l = findResources(cloudFormation,"AWS::EC2::Subnet")
                for s in subnet:
                    if not s in l:
                        for y in l:
                            log("INFO",f" - {y}")
                        log("FATAL",f"Subnet {s} not found")

                if f'{name}Subnets' in cloudFormation['Parameters']:
                    log("WARNING",f"Deleting parameter {name}Subnets")
                    del cloudFormation['Parameters'][f'{name}Subnets']
            else:
                subnet = f"{name}Subnets"
                log("INFO",f"Creating parameter {name}Subnets")
                cloudFormation['Parameters'][f'{name}Subnets'] = parameter_Subnets()
                
            # -- look for launch templates - if we find only 1, use it
            LT = findResources(cloudFormation,'AWS::EC2::LaunchTemplate')
            
            if len(LT) == 1:
                lt = LT[0]
            elif len(LT) > 1:
                if not args.lt:
                    log("FATAL","There are too many launch templates - select one with the -lt option")
                if not args.lt in LT:
                    log("FATAL","You provided an unknown launch template")
                else:
                    lt = args.lt
            else:
                log("FATAL","There are no launch templates available.")

            log("INFO",f"- Using Launch Template {lt}")
            if type(subnet)==list:
                VPCZoneIdentifier = []
                for x in subnet:
                    VPCZoneIdentifier.append({"Ref" : x })               
            else:
                VPCZoneIdentifier = { "Ref" : subnet}

            cloudFormation['Resources'][f"{name}AutoScaling"] = resource_autoscaling(name,lt,VPCZoneIdentifier)
        elif resource == 'securitygroup':
            # -- we stick to a single VPC.  The chances of someone creating more than 1 VPC in a CF template is low.
            vpcs = findResources(cloudFormation,"AWS::EC2::VPC")
            if len(vpcs) == 0:
                cloudFormation['Parameters']['VpcId'] = parameter_vpc()
                vpc = 'VpcId'
            else:
                vpc = vpcs[0]
                log("WARNING",f"Security Group will be created in VPC {vpc}")
                if 'VpcId' in cloudFormation['Parameters']:
                    del(cloudFormation['Parameters']['VpcId'])
                    log("WARNING","Removing parameter VpcId")
                    

            cloudFormation['Resources'][name] = resource_securitygroup_web(vpc)
        elif resource == 'ec2':
            if args.subnet:
                subnet = args.subnet
                if f"{name}Subnet" in cloudFormation['Parameters']:
                    log("WARNING",f"Deleting parameter - {name}Subnet")
                    del cloudFormation['Parameters'][f"{name}Subnet"]
            else:
                subnet = f"{name}Subnet"

                for x in findResources(cloudFormation,"AWS::EC2::Subnet"):
                    log("INFO",f" - Found subnet - {x}")
                
                log("WARNING","Specify -subnet to define a subnet to use for this instance. Defaults to parameter")
                cloudFormation['Parameters'][subnet] = parameter_Subnet()

            mySG = request_sg(name,cloudFormation,args)
            cloudFormation['Parameters']['LatestAmiId'] = parameter_LatestAmiId()
            cloudFormation['Resources'][f"{name}ec2Role"] = resource_ec2Role()
            cloudFormation['Resources'][f"{name}ec2InstanceProfile"] = resource_ec2InstanceProfile(f"{name}ec2Role")
            cloudFormation['Resources'][name] = resource_ec2Instance(f"{name}ec2InstanceProfile",'LatestAmiId',mySG,subnet)
        elif resource == 'vpc':
            cloudFormation['Resources'][name] = resource_vpc("10.0.0.0/22")
            cloudFormation['Resources'][f"{name}SubnetA0"] = resource_vpc_subnet(name,"10.0.0.0/24",0,{ "MapPublicIpOnLaunch" : True})
            cloudFormation['Resources'][f"{name}SubnetB0"] = resource_vpc_subnet(name,"10.0.1.0/24",1,{ "MapPublicIpOnLaunch" : True})
            cloudFormation['Resources'][f"{name}SubnetA1"] = resource_vpc_subnet(name,"10.0.2.0/24",0,{ "MapPublicIpOnLaunch" : False})
            cloudFormation['Resources'][f"{name}SubnetB1"] = resource_vpc_subnet(name,"10.0.3.0/24",1,{ "MapPublicIpOnLaunch" : False})
            cloudFormation['Resources'][f"{name}igw"] = resource_vpc_igw()
            cloudFormation['Resources'][f"{name}igwattachment"] = resource_vpc_igw_attachment(f"{name}igw",name)
            cloudFormation['Resources'][f"{name}RouteTable"] = resource_vpc_route_table(name)
            cloudFormation['Resources'][f"{name}RouteIGW"] = resource_vpc_default_route_igw(f"{name}igw",f"{name}RouteTable")
            cloudFormation['Resources'][f"{name}SubnetA0Route"] = resource_vpc_subnet_route(f"{name}SubnetA0",f"{name}RouteTable")
            cloudFormation['Resources'][f"{name}SubnetB0Route"] = resource_vpc_subnet_route(f"{name}SubnetB0",f"{name}RouteTable")
            cloudFormation['Resources'][f"{name}SubnetA1Route"] = resource_vpc_subnet_route(f"{name}SubnetA1",f"{name}RouteTable")
            cloudFormation['Resources'][f"{name}SubnetB1Route"] = resource_vpc_subnet_route(f"{name}SubnetB1",f"{name}RouteTable")



        else:
            log("FATAL",f"Unknown resource type - {resource}")
            
        # -- Update the code for all Lambda function
        for name in cloudFormation['Resources']:
            if cloudFormation['Resources'][name]['Type'] == 'AWS::Lambda::Function':
                if os.path.exists(f"{name}.py"):
                    log("INFO",f"Found {name}.py - Updating Lambda function {name}")
                    # TODO - if the file is too big, Lambda will not update it
                    with open(f"{name}.py",'rt') as C:
                        pc = C.readlines()
                        cloudFormation['Resources'][name]['Properties']['Code']['ZipFile'] =  { "Fn::Join": ["", pc ]}

        # -- Update EC2 Launch Template UserData
        for name in cloudFormation['Resources']:
            if os.path.exists(f"{name}.sh"):
                with open(f"{name}.sh",'rt') as C:
                    pc = C.readlines()

                if cloudFormation['Resources'][name]['Type'] == 'AWS::EC2::LaunchTemplate':
                    log("INFO",f"Found {name}.sh - Updating Launch Template User Data {name}")
                    cloudFormation['Resources'][name]['Properties']['LaunchTemplateData']['UserData'] = { "Fn::Base64": {"Fn::Join": [ "", pc ] } }
                if cloudFormation['Resources'][name]['Type'] == 'AWS::EC2::Instance':
                    log("INFO",f"Found {name}.sh - Updating Launch Template User Data {name}")
                    cloudFormation['Resources'][name]['Properties']['UserData'] = { "Fn::Base64": {"Fn::Join": [ "", pc ] } }

    # == link resources to each other
    if args.link:
        # -- linking s3 to lambda
        if cloudFormation['Resources'][args.link[0]]['Type'] == 'AWS::S3::Bucket' and cloudFormation['Resources'][args.link[1]]['Type'] == 'AWS::Lambda::Function':
            log("INFO","Linking S3 to Lambda")

            # -- update the Lambda variable
            cloudFormation['Resources'][args.link[1]]['Properties']['Environment']['Variables'][args.link[0]] = { "Ref" : args.link[0] } 
            
            # -- update the Lamdba Execution Role policy
            x = cloudFormation['Resources'][f"{args.link[1]}ExecutionRole"]['Properties']['Policies'][0]['PolicyDocument']['Statement']

            p = {
                "Effect" : "Allow",
                "Action" : [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:DeleteObject",
                    "s3:ListBuckets"
                ],
                "Resource" : {
                    "Fn::Join": [ "", [ "arn:aws:s3:::", { "Ref": args.link[0] }, "/*" ] ]
                }
            }
            if not p in x:
                log("WARNING","Updating policy")
                x.append(p)
            else:
                log("INFO","Policy unchanged")

        else:
            log("FATAL","Unsupported linking direction")

        
    #print(json.dumps(cloudFormation, indent=4))

    log("INFO",f"Writing {args.cf}")
    result = json.dumps(cloudFormation,indent=4)
    with open(args.cf,"wt") as Q:
        Q.write(result)

if __name__ == '__main__':
    main()

