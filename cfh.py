import json
import os
import argparse
import boto3
import re

# =========================== Parameter Templates ===========================

def parameter_LatestAmiId():
    return {
        "Type" : "AWS::SSM::Parameter::Value<AWS::EC2::Image::Id>",
        "Default" : "/aws/service/ami-amazon-linux-latest/amzn2-ami-hvm-x86_64-gp2",
        "Description" : "Path to the SSM Parameter that contains the latest Amazon Linux 2 image ID"
    }

def parameter_String(desc):
    return {
        "Type" : "String",
        "Description" : desc
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

def resource_ec2Instance(name,IamInstanceProfile,ImageId,SecurityGroup, Subnet):
    return {
        "Type" : "AWS::EC2::Instance",
        "Properties" : {
            "ImageId" : { "Ref" : ImageId },
            "IamInstanceProfile"    : { "Ref" : IamInstanceProfile },
            "InstanceType" : "t2.micro",
            "NetworkInterfaces": [ {
                #"AssociatePublicIpAddress": "true",
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

def resource_eip():
    return  {
        "Type" : "AWS::EC2::EIP",
        "Properties" : {
            "Domain" : "vpc"
        }
    }

def resource_eventbridge_schedule(name,cron):
    return {
    "Type": "AWS::Events::Rule",
    "Properties": {
        "Description": f"Scheduled event to trigger the Lambda function {name}",
        "ScheduleExpression" : cron,
        "State": "ENABLED",
        "Targets": [{ 
            "Arn": { "Fn::GetAtt": [ name, "Arn" ] },
            "Id" : { "Fn::Sub": f"${{AWS::StackName}}-{name}" }
        } ]
    }
}

def resource_functionurl(target):
    return {
        "Type" : "AWS::Lambda::Url",
        "Properties" : {
            "AuthType" : "NONE",
            #"InvokeMode" : String,
            #"Qualifier" : String,
            "TargetFunctionArn" : { "Ref" : target }
        }
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

def resource_lambda_permission(name,event):
    return {
        "Type": "AWS::Lambda::Permission",
        "Properties": {
            "FunctionName": { "Ref": name },
            "Action": "lambda:InvokeFunction",
            "Principal": "events.amazonaws.com",
            "SourceArn": { "Fn::GetAtt": [event, "Arn"] }
        }
    }

def resource_lambda_function_public_permission(name):
    return {
        "Type": "AWS::Lambda::Permission",
        "Properties": {
            "FunctionName": { "Ref": name },
            "Action": "lambda:InvokeFunctionUrl",
            "Principal": "*",
            "FunctionUrlAuthType" : "NONE"
        }
    }

def resource_natgateway(subnet,eip):
    return {
        "Type" : "AWS::EC2::NatGateway",
        "Properties" : {
            "AllocationId" : { "Fn::GetAtt" : [eip, "AllocationId"] },
            "SubnetId" : { "Ref" : subnet },
        }
    }

def resource_rds_subnetgroup(DBSubnetGroupDescription,subnets):
    SubnetIds = []
    for s in subnets:
        SubnetIds.append({ "Ref" : s})
    return {
        "Type": "AWS::RDS::DBSubnetGroup",
        "Properties": {
            "DBSubnetGroupDescription" : DBSubnetGroupDescription,
            "SubnetIds": SubnetIds,
        }
    }

def resource_rds(name,username,password,sg):
    return {
        "Type": "AWS::RDS::DBInstance",
        "Properties" : {
                "DBName" : name,
                "AllocatedStorage": 20,
                "DBInstanceClass" : "db.t3.micro",
                "AutoMinorVersionUpgrade": True,
                "Engine" : "mysql",
                "MasterUsername" : { "Ref" : username },
                "MasterUserPassword" : { "Ref" : password },
                "MultiAZ" : False,
                "VPCSecurityGroups" : [ { "Ref" : sg } ],
                "DBSubnetGroupName" : { "Ref" : f"{name}SubnetGroup" } 
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

def resource_securitygroup(vpc):
    return {
        "Type": "AWS::EC2::SecurityGroup",
        "Properties": {
            "GroupDescription": "Security Group",
            "SecurityGroupIngress" : [],
            "SecurityGroupEgress" : [],
            "VpcId": { "Ref": vpc }
        }
    }

def resource_ssm_parameter(name,value):
    return {
        "Type": "AWS::SSM::Parameter",
        "Properties": {
            "Name": name,
            "Value": value,
            "Type": "String",
            "Description": name,
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

def resource_vpc_default_route_natgateway(natgateway,routeTable):
    return {
        "Type" : "AWS::EC2::Route",
        "Properties" : {
            "RouteTableId" : { "Ref" :  routeTable  },
            "DestinationCidrBlock" : "0.0.0.0/0",
            "NatGatewayId" : { "Ref" : natgateway }
        },
        "DependsOn" : [ natgateway, routeTable ]
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

def policy_s3bucket(bucket):
    return {
        "Effect" : "Allow",
        "Action" : [
            "s3:GetObject",
            "s3:PutObject",
            "s3:DeleteObject",
            "s3:ListBuckets"
        ],
        "Resource" : [
            { "Fn::Sub": "arn:${AWS::Partition}:s3:::" + bucket + "/*" }
        ]
    }

def policy_ssm_parameter(parameter):
    return {
        "Effect" : "Allow",
        "Action" : [
            "ssm:GetParameter",
        ],
        "Resource" : [
            { "Fn::Sub": "arn:${AWS::Partition}:ssm:${AWS::Region}:${AWS::AccountId}:parameter/" + parameter }
        ]
    }
# =========================== Other code procedures ===========================

def log(e,t):
    if e != '':
        print(f"[{e}] {t}")
    else:
        print("---------------------------------------")
        print(f"{t}")
        print("---------------------------------------")

    if e == "FATAL":
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
            if not args.cidr:
                log("FATAL","Provide the CIDR range for this VPC")
            cloudFormation['Resources'][name] = resource_vpc(args.cidr)
            cloudFormation['Resources'][f"{name}InternetGateway"] = resource_vpc_igw()
            cloudFormation['Resources'][f"{name}InternetGatewayAttachment"] = resource_vpc_igw_attachment(f"{name}InternetGateway",name)
            cloudFormation['Resources'][f"{name}RouteTableInternetGateway"] = resource_vpc_route_table(name)
            cloudFormation['Resources'][f"{name}RouteInternetGateway"] = resource_vpc_default_route_igw(f"{name}InternetGateway",f"{name}RouteTableInternetGateway")
        elif resource == 'publicsubnet':
            if not args.cidr:
                log("FATAL","Provide the CIDR range for this subnet")
            if not args.az:
                log("FATAL","Provide the AZ (-az) to use (use 0,1,2 - this is an array reference)")
            vpc = resourceSelector(cloudFormation,args.vpc,"AWS::EC2::VPC")
            RouteTable = resourceSelector(cloudFormation,args.routetable,"AWS::EC2::RouteTable")
            cloudFormation['Resources'][f"{name}"] = resource_vpc_subnet(vpc,args.cidr,args.az,{ "MapPublicIpOnLaunch" : True})
            cloudFormation['Resources'][f"{name}Route"] = resource_vpc_subnet_route(f"{name}",RouteTable)
        elif resource == 'privatesubnet':
            if not args.cidr:
                log("FATAL","Provide the CIDR range for this VPC")
            if not args.az:
                log("FATAL","Provide the AZ (-az) to use (use 0,1,2 - this is an array reference)")
            
            vpc = resourceSelector(cloudFormation,args.vpc,"AWS::EC2::VPC")
            RouteTable = resourceSelector(cloudFormation,args.routetable,"AWS::EC2::RouteTable")

            cloudFormation['Resources'][f"{name}"] = resource_vpc_subnet(vpc,args.cidr,args.az,{})
            cloudFormation['Resources'][f"{name}Route"] = resource_vpc_subnet_route(f"{name}",RouteTable)
        elif resource == 'securitygroup':
            vpc = resourceSelector(cloudFormation,args.vpc,"AWS::EC2::VPC","VpcId","AWS::EC2::VPC::Id")
            if not name in cloudFormation['Resources']:
                cloudFormation['Resources'][name] = resource_securitygroup(vpc)

            if args.ingress:
                cloudFormation['Resources'][name]['Properties']['SecurityGroupIngress'].append(
                    securityGroupRule(cloudFormation,args.ingress,args.tcp,args.udp)
                )
            if args.egress:
                cloudFormation['Resources'][name]['Properties']['SecurityGroupEgress'].append(
                    securityGroupRule(cloudFormation,args.egress,args.tcp,args.udp)
                )
        elif resource == 's3':
            cloudFormation['Resources'][name] = resource_s3()
        elif resource == 'ec2':
            subnet = resourceSelector(cloudFormation,args.subnet,"AWS::EC2::Subnet",f"{name}Subnet","AWS::EC2::Subnet::Id")
            mySG = resourceSelector(cloudFormation,args.sg,"AWS::EC2::SecurityGroup",f"{name}SecurityGroup","AWS::EC2::SecurityGroup::Id")
            
            cloudFormation['Parameters']['LatestAmiId'] = parameter_LatestAmiId()
            cloudFormation['Resources'][f"{name}ec2Role"] = resource_ec2Role()
            cloudFormation['Resources'][f"{name}ec2InstanceProfile"] = resource_ec2InstanceProfile(f"{name}ec2Role")
            cloudFormation['Resources'][name] = resource_ec2Instance(name,f"{name}ec2InstanceProfile",'LatestAmiId',mySG,subnet)
        elif resource == 'static':
            cloudFormation['Resources'][name] = resource_static()
            cloudFormation['Resources'][f"{name}bucketPolicy"] = resource_static_bucketPolicy(name)
            cloudFormation['Outputs'][name] = {
                "Value" : { "Fn::GetAtt" : [ name, "WebsiteURL" ] },
                "Description": "URL for website hosted on S3"
            }
    
        elif resource == 'natgateway':
            subnet = resourceSelector(cloudFormation,args.subnet,"AWS::EC2::Subnet")
            vpc = resourceSelector(cloudFormation,args.vpc,"AWS::EC2::VPC")
            
            cloudFormation['Resources'][f"{name}ElasticIP"] = resource_eip()
            cloudFormation['Resources'][name] = resource_natgateway(subnet,f"{name}ElasticIP")
            cloudFormation['Resources'][f"{name}RouteTableNATGateway"] = resource_vpc_route_table(vpc)
            cloudFormation['Resources'][f"{name}RouteNATGateway"] = resource_vpc_default_route_natgateway(f"{name}",f"{name}RouteTableNATGateway")
        elif resource == 'lambda':
            cloudFormation['Resources'][name] = resource_lambda(name)
            cloudFormation['Resources'][f"{name}ExecutionRole"] = resource_lambda_ExecutionRole(name)
            log("INFO",f'Create a file called {name}.py to cause cfh to update the code automatically')
        elif resource == 'launchtemplate':
            mySG = resourceSelector(cloudFormation,args.sg,"AWS::EC2::SecurityGroup",f"{name}SecurityGroup","AWS::EC2::SecurityGroup::Id")
            cloudFormation['Parameters']['LatestAmiId'] = parameter_LatestAmiId()
            cloudFormation['Resources'][f"{name}ec2Role"] = resource_ec2Role()
            cloudFormation['Resources'][f"{name}ec2InstanceProfile"] = resource_ec2InstanceProfile(f"{name}ec2Role")
            cloudFormation['Resources'][f"{name}"] = resource_ec2LaunchTemplate(name,f"{name}ec2InstanceProfile","LatestAmiId",mySG)
        elif resource == 'autoscaling':
            subnets = resourceSelector(cloudFormation,args.subnet,'AWS::EC2::Subnet',f"{name}Subnets","List<AWS::EC2::Subnet::Id>").split(',')
            lt = resourceSelector(cloudFormation,args.lt,'AWS::EC2::LaunchTemplate')
            VPCZoneIdentifier = []
            for x in subnets:
                VPCZoneIdentifier.append({"Ref" : x })               
            cloudFormation['Resources'][f"{name}AutoScaling"] = resource_autoscaling(name,lt,VPCZoneIdentifier)    
        elif resource == "parameter":
            cloudFormation['Parameters'][name] = parameter_String(name)
        elif resource == 'eventbridge':
            if not args.cron:
                log("FATAL","eventbridge needs a -cron parameter")
            
            if not args.target:
                log("FATAL","eventbridge needs a -target parameter")
            
            # -- confirm that target actually exists
            if cloudFormation['Resources'].get(args.target,{})['Type'] == "AWS::Lambda::Function":
                cloudFormation['Resources'][name] = resource_eventbridge_schedule(args.target,args.cron)
                cloudFormation['Resources'][f"{name}lambdaPermission"] = resource_lambda_permission(args.target,name)
            else:
                log("FATAL","event bridge -target does not exist or is not a Lambda function")
        elif resource == 'functionurl':
            if not args.target:
                log("FATAL","functionurl needs a -targe parameter")

            cloudFormation['Resources'][name] = resource_functionurl(args.target)
            cloudFormation['Resources'][f"{name}permission"] = resource_lambda_function_public_permission(name)
            cloudFormation['Outputs'][name] = {
                "Value" : { "Fn::GetAtt" : [ name, "FunctionUrl" ] },
                "Description": "URL for Lambda function"
            }
        elif resource == 'ssmparameter':
            if not args.value:
                log("FATAL","Missing -value parameter")
            cloudFormation['Resources'][name] = resource_ssm_parameter(name,args.value)
        elif resource == 'rds':
            cloudFormation['Parameters'][f"{name}MasterUserName"] = parameter_String(f"{name}MasterUserName")
            cloudFormation['Parameters'][f"{name}MasterPassword"] = parameter_String(f"{name}MasterPassword")

            subnets = resourceSelector(cloudFormation,args.subnet,'AWS::EC2::Subnet',f"{name}Subnets","List<AWS::EC2::Subnet::Id>").split(',')
            mySG = resourceSelector(cloudFormation,args.sg,"AWS::EC2::SecurityGroup",f"{name}SecurityGroup","AWS::EC2::SecurityGroup::Id")

            cloudFormation['Resources'][name] = resource_rds(name,f"{name}MasterUserName",f"{name}MasterPassword",mySG)
            cloudFormation['Resources'][f"{name}SubnetGroup"] = resource_rds_subnetgroup(name,subnets)

            cloudFormation['Outputs'][name] = {
                "Value" : { "Fn::GetAtt" : [ name, "Endpoint.Address" ] },
                "Description": "Database Endpoint"
            }


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
            if os.path.exists(f"{name}.py"):
                log("INFO",f"Found {name}.py - Updating Lambda function {name}")
                # TODO - if the file is too big, Lambda will not update it
                with open(f"{name}.py",'rt') as C:
                    pc = C.readlines()
                    cloudFormation['Resources'][name]['Properties']['Code']['ZipFile'] =  { "Fn::Join": ["", pc ]}

    # == Update EC2 Launch Template UserData
    for name in cloudFormation['Resources']:
        if os.path.exists(f"{name}.sh"):
            with open(f"{name}.sh",'rt') as C:
                pc = C.readlines()

            if cloudFormation['Resources'][name]['Type'] == 'AWS::EC2::LaunchTemplate':
                log("INFO",f"Found {name}.sh - Updating Launch Template User Data {name}")
                cloudFormation['Resources'][name]['Properties']['LaunchTemplateData']['UserData'] = { "Fn::Base64": {"Fn::Join": [ "", pc ] } }
            if cloudFormation['Resources'][name]['Type'] == 'AWS::EC2::Instance':
                log("INFO",f"Found {name}.sh - Updating EC2 User Data {name}")
                cloudFormation['Resources'][name]['Properties']['UserData'] = { "Fn::Base64": {"Fn::Join": [ "", pc ] } }

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
                
                p = policy_s3bucket(args.link[0])
                
                if not p in x:
                    log("WARNING","Updating policy")
                    x.append(p)
                else:
                    log("INFO","Policy unchanged")

            # -- linking s3 to lambda
            if cloudFormation['Resources'][args.link[0]]['Type'] == 'AWS::S3::Bucket' and cloudFormation['Resources'][args.link[1]]['Type'] == 'AWS::Lambda::Function':
                log("INFO",f"Linking S3 ({args.link[0]}) to Lambda ({args.link[1]})")

                # -- update the Lambda variable
                cloudFormation['Resources'][args.link[1]]['Properties']['Environment']['Variables'][args.link[0]] = { "Ref" : args.link[0] } 
                
                # -- update the Lambda Execution Role policy
                x = cloudFormation['Resources'][f"{args.link[1]}ExecutionRole"]['Properties']['Policies'][0]['PolicyDocument']['Statement']

                p = policy_s3bucket(args.link[0])
                
                if not p in x:
                    log("WARNING","Updating policy")
                    x.append(p)
                else:
                    log("INFO","Policy unchanged")

            # -- linking ssm parameter to lambda
            if cloudFormation['Resources'][args.link[0]]['Type'] == 'AWS::SSM::Parameter' and cloudFormation['Resources'][args.link[1]]['Type'] == 'AWS::Lambda::Function':
                log("INFO",f"Linking SSM Parameter ({args.link[0]}) to Lambda ({args.link[1]})")

                # -- update the Lambda variable
                cloudFormation['Resources'][args.link[1]]['Properties']['Environment']['Variables'][args.link[0]] = "{{resolve:ssm:" + args.link[0] + "}}" #{ "Ref" : args.link[0] } 
                
                # -- update the Lambda Execution Role policy
                x = cloudFormation['Resources'][f"{args.link[1]}ExecutionRole"]['Properties']['Policies'][0]['PolicyDocument']['Statement']

                p = policy_ssm_parameter(args.link[0])
                
                if not p in x:
                    log("WARNING","Updating policy")
                    x.append(p)
                else:
                    log("INFO","Policy unchanged")

            #else:
                #log("FATAL","Unsupported linking direction")

        
    #print(json.dumps(cloudFormation, indent=4))

    log("INFO",f"Writing {args.cf}")
    result = json.dumps(cloudFormation,indent=4)
    with open(args.cf,"wt") as Q:
        Q.write(result)

    if args.updatestack:
        log("WARNING","====================================================================")
        log("WARNING",f"UPDATING CLOUDFORMATION STACK - {args.updatestack}")
        response = boto3.client('cloudformation').update_stack(  
            StackName = args.updatestack,
            TemplateBody = result,  
            Capabilities = ['CAPABILITY_IAM']  
        )
        if 'StackId' in response:
            log("INFO",response['StackId'])
        else:
            print(response)
        log("WARNING","====================================================================")

    # print("-----------------------")
    # print("To update your stack, run:")
    # print("")
    # print(f"aws cloudformation update-stack --template-body file://{args.cf} --capabilities CAPABILITY_IAM --stack-name YOURSTACKNAME")
    # print("")
    # print("To create a new stack, run:")
    # print("")
    # print(f"aws cloudformation create-stack --template-body file://{args.cf} --capabilities CAPABILITY_IAM --stack-name YOURSTACKNAME")

if __name__ == '__main__':
    main()

