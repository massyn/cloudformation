# CloudFormation Helper
Cloudformation Helper script

[![Testing](https://github.com/massyn/cloudformation/actions/workflows/test.yml/badge.svg)](https://github.com/massyn/cloudformation/actions/workflows/test.yml)

## What is CloudFormation Helper?

CloudFormation Helper is a tool to help you add resources to CloudFormation templates, create basic links between resources, or update code used in EC2 UserData, or Lambda functions.

This tool uses no state files and does not know your AWS environment.  It is simply a tool that touches your CloudFormation json file by adding (or slightly modifying existing) resources.  The basic idea of the tool is to stand up some basic infrastructure, and allow you to then customise the CloudFormation template how you see fit.

It also has the built-in capability to update Lambda function code, or EC2 UserData, without requiring you manually edit the files.

CFH is not intended to be a replacement for tools like Teraform or CDK, which are already much more advanced and mature than CFH.  This tool is for situations where the result is a CloudFormation template, and you require some assistance to add some resources to the template.  Instead of simply disregarding all the good work you've already done, where a need exists to create a new CloudFormation template from scratch, you can use CFH to do some of the heavy lifting for you.

## Caveats

* CFH is not a replacement for Teraform or CDK.  Its purpose is to create a basic template, then it is up to you to customise.
* Not all possible use cases and scenarios will be catered for.  The goal is to provide a template very quickly to get you up and running.  Any customisation is up to you.

## Features of the tool

### Adding resources

`python cfh.py -cf template.json -add s3 myS3Bucket`

### Listing all resources

`python cfh.py -cf template.json -list`

### Adding parameters

`python cfh.py -cf template.json -add parameter myParameter`

### Linking dependencies

`python cfh.py -cf template.json -link myS3Bucket myLambdaFunction`

### Updating Lambda functions code

CFH will check if a file called `{name}.py` exists - if it does, it will replace the `Code` section of the template with the contents of this file.

### Updating EC2 UserData

CFH will check if a file called `{name}.sh` exists - if it does, it will replace the `UserData` section of an EC2 instance or a launch template with the contents of this file.

### Updating the stack on AWS (experimental)

`python cfh.py -cf template.json -updatestack MyStackName`

## Wish list for a future version

### New Resources

* sns
* sqs
* Add docker lambda

### Functional

* Use yaml files instead of json
* Add docker containers (EKS?? / Lambda??)
* Create the stack directly
* Delete individual resources

### Linking

* EC2 Roles to invoke Lambda
* EC2 Roles to SSM Parameters

## Use cases

> WARNING - These examples are provided to demonstrate the capabilities of the tool.  You do run the risk of creating stacks that will most likely cost you money, so be careful what you deploy on your AWS accounts.  Components like the NAT Gateway are NOT free, and if you happen to leave it running, you will incur charges.

### Serverless function to harvest data from a URL

This use case will create a Lambda function URL that will take all the input data it receives, and store it in a DynamoDB table.

|**Description**|**Command**|
|--|--|
|Create the basic template.|`python cfh.py -cf usecase1.json -desc "Use case 1 - Function URL to DynamoDB example"`|
|Create the Lambda function|`python cfh.py -cf usecase1.json -add lambda usecase1lambda`|
|Create the function URL, linked to the lambda function|`python cfh.py -cf usecase1.json -add functionurl myFunctionUrl -target usecase1lambda`|
|Create your DynamoDB table|`python cfh.py -cf usecase1.json -add dynamodb myDynamoDbTable`|
|Link the DynamoDB table to the Lambda function, allowing it permission to access the table|`python cfh.py -cf usecase1.json -link myDynamoDbTable usecase1lambda`|

Provided the file `usecase1lambda.py` is in the same folder, it will be picked up and embedded in the Cloudformation template.

### Static website updated every 5 minutes

Using an Event Bridge schedule to trigger a lambda function every 5 minutes that will write a message to a static S3-hosted website.

|**Description**|**Command**|
|--|--|
|Create the basic template|`python cfh.py -cf usecase2.json -desc "Use case 2 - Scheduled lambda to update a website"`|`|
|Create the lambda function|`python cfh.py -cf usecase2.json -add lambda usecase2lambda`|
|Create a static S3 website|`python cfh.py -cf usecase2.json -add static myStaticS3`|
|Create an event bridge schedule to trigger the lambda function every 5 minutes|`python cfh.py -cf usecase2.json -add eventbridge myEventBridge -cron "rate(5 minutes)" -target usecase2lambda`|
|Add a CloudFormation parameter that will be filled in by the user when they deploy the template|`python cfh.py -cf usecase2.json -add parameter websiteMessage`|
|Create a parameter in the SSM Parameter store with a default value|`python cfh.py -cf usecase2.json -add ssmparameter mySSMParameterStore -value "Hello there!"`|
|Give the Lambda function permissions to access the S3 bucket|`python cfh.py -cf usecase2.json -link myStaticS3 usecase2lambda`|
|Pass the cloudformation parameter value to the lambda function|`python cfh.py -cf usecase2.json -link websiteMessage usecase2lambda`|
|Give the Lambda function permissions to access the SSM Parameter store|`python cfh.py -cf usecase2.json -link mySSMParameterStore usecase2lambda`|

### Create Bastion server

This use case will create a EC2 server.  Without specifying the Vpc or subnet, it will add parameters to the template.

|**Description**|**Command**|
|--|--|
|Create the basic template|`python cfh.py -cf usecase3.json -desc "Use case 3 - Bastion server"`|
|Create a security group to allow Port 22 from the internet|`python cfh.py -cf usecase3.json -add securitygroup SGBastion -ingress 0.0.0.0/0 -tcp 22`|
|Add an egress for all ports to the security group|`python cfh.py -cf usecase3.json -add securitygroup SGBastion -egress 0.0.0.0/0`|
|Add an EC2 instance, and attach the security group to it|`python cfh.py -cf usecase3.json -add ec2 BastionServer -sg SGBastion`|
|Update the properties of the EC2 instance to use a specific key|`python cfh.py -cf usecase3.json -properties BastionServer KeyName ap-southeast-2-2022`|

### Create a redundant and secure web platform

The following example is a highly redundant, very secure, 3-tier web server configuration.  It features 2 public subnets, and 2 private subnets, with an autoscaling load-balancer protecting the web servers from direct internet access.

|**Description**|**Command**|
|--|--|
|Create the basic template|`python cfh.py -cf usecase4.json -desc "Use case 4 - Complex Wordpress example"`|
|Create a VPC|`python cfh.py -cf usecase4.json -add vpc myVPC -cidr 10.0.0.0/22`|
|Create two public subnets, one in each availability zone|`python cfh.py -cf usecase4.json -add publicsubnet myPublicSubnetA -az 0 -vpc myVPC -cidr 10.0.0.0/24`|
||`python cfh.py -cf usecase4.json -add publicsubnet myPublicSubnetB -az 1 -vpc myVPC -cidr 10.0.1.0/24`|
|Create a security group for the load balancer to allow inbound web traffic|`python cfh.py -cf usecase4.json -add securitygroup SGWebInbound -vpc myVPC -ingress 0.0.0.0/0 -tcp 80`|
||`python cfh.py -cf usecase4.json -add securitygroup SGWebInbound -vpc myVPC -ingress 0.0.0.0/0 -tcp 443`|
|The same security group should also allow outgoing traffic|`python cfh.py -cf usecase4.json -add securitygroup SGWebInbound -vpc myVPC -egress 0.0.0.0/0`|
|Create a security group to allow the web server to communicate with the load balancer|`python cfh.py -cf usecase4.json -add securitygroup SGWebServer -vpc myVPC -ingress SGWebInbound -tcp 80`|
||`python cfh.py -cf usecase4.json -add securitygroup SGWebServer -vpc myVPC -ingress SGWebInbound -tcp 443`|
||`python cfh.py -cf usecase4.json -add securitygroup SGWebServer -vpc myVPC -egress 0.0.0.0/0`|
|Create a security group to allow the web server to talk to the database|`python cfh.py -cf usecase4.json -add securitygroup SGdatabase -vpc myVPC -egress 0.0.0.0/0`|
||`python cfh.py -cf usecase4.json -add securitygroup SGdatabase -vpc myVPC -ingress SGWebServer -tcp 3306`|
|Create a NAT gateway to allow private subnets to reach the internet for patching|`python cfh.py -cf usecase4.json -add natgateway myNatGateway -subnet myPublicSubnetA`|
|Create 2 private subnets linked to the NAT gateway|`python cfh.py -cf usecase4.json -add privatesubnet myPrivateSubnetA -az 0 -vpc myVPC -cidr 10.0.2.0/24 -routetable myNatGatewayRouteTableNATGateway`|
||`python cfh.py -cf usecase4.json -add privatesubnet myPrivateSubnetB -az 1 -vpc myVPC -cidr 10.0.3.0/24 -routetable myNatGatewayRouteTableNATGateway`|
|Create a launch template for the web server|`python cfh.py -cf usecase4.json -add launchtemplate usecase4WordpressLaunchTemplate -sg SGWebServer`|
|Attach the launch template to an auto scaling group|`python cfh.py -cf usecase4.json -add autoscaling myAutoscalingGroup -lt usecase4WordpressLaunchTemplate -subnet myPrivateSubnetA,myPrivateSubnetB -vpc myVPC`|
|Create a load balancer|`python cfh.py -cf usecase4.json -add elbv2 myELBv2 -sg SGWebInbound -subnet myPublicSubnetA,myPublicSubnetB`|
|Create an RDS mySQL database|`python cfh.py -cf usecase4.json -add rds myDatabase -subnet myPrivateSubnetA,myPrivateSubnetB -sg SGdatabase`|

## Reference guide

### -add resource options

|**Option**|**Parameters**|**Resources**|**name**|
|--|--|--|--|
|`vpc`|`-cidr`|||
|||AWS::EC2::VPC|{name}|
|||AWS::EC2::InternetGateway|{name}InternetGateway|
|||AWS::EC2::VPCGatewayAttachment|{name}InternetGatewayAttachment|
|||AWS::EC2::RouteTable|{name}RouteTableInternetGateway|
|||AWS::EC2::Route|{name}RouteInternetGateway|
|`natgateway`|`-subnet` `-vpc` (`-routetable`)|||
|||AWS::EC2::NatGateway|{name}|
|||AWS::EC2::EIP|{name}ElasticIP|
|||AWS::EC2::RouteTable|{name}RouteTableNATGateway|
|||AWS::EC2::Route|{name}RouteNATGateway|
|`publicsubnet`|`-vpc` `-az` `-cidr`|||
|||AWS::EC2::Subnet|{name}|
|||AWS::EC2::SubnetRouteTableAssociation|{name}Route|
|`privatesubnet`|`-vpc` `-az` `-cidr`|||
|||AWS::EC2::Subnet|{name}|
|||AWS::EC2::SubnetRouteTableAssociation|{name}Route|
|`securitygroup`|(`-vpc`)|||
|||AWS::EC2::SecurityGroup|{name}|
|`s3`||||
|||AWS::S3::Bucket|{name}|
|`ec2`|`-subnet` `-sg`|||
|||AWS::EC2::Instance|{name}|
|||AWS::IAM::Role|{name}ec2Role|
|||AWS::IAM::InstanceProfile|{name}ec2InstanceProfile|
|`static`|||||
|||AWS::S3::Bucket|{name}|
|||AWS::S3::BucketPolicy|{name}BucketPolicy|
|`lambda`|||||
|||AWS::Lambda::Function|{name}|
|||AWS::IAM::Role|{name}ExecutionRole|
|`launchtemplate`|`-sg`||||
|||AWS::EC2::LaunchTemplate|{name}|
|||AWS::IAM::Role|{name}ec2Role|
|||AWS::IAM::InstanceProfile|{name}ec2InstanceProfile|
|`autoscaling`|`-lt` `-subnets` `-vpc`||||
|||AWS::AutoScaling::AutoScalingGroup|{name}|
|||AWS::ElasticLoadBalancingV2::TargetGroup|{Name}TargetGroup|
|`elbv2`|`-sg` `-subnets` `-target`||||
|||AWS::ElasticLoadBalancingV2::LoadBalancer|{name}|
|||AWS::ElasticLoadBalancingV2::Listener|{name}Listener|
|||AWS::ElasticLoadBalancingV2::Listener|{name}ListenerRedirect|
|`eventbridge`|`-cron` `-target`||||
|||AWS::Events::Rule|{name}|
|||AWS::Lambda::Permission|{name}lambdaPermission|
|`functionurl`|`-target`||||
|||AWS::Lambda::Url|{name}|
|||AWS::Lambda::Permission|{name}permission|
|`ssmparameter`|`-value`||||
|||AWS::SSM::Parameter|{name}|
|`rds`|`-subnet` `-sg`||||
|||AWS::RDS::DBInstance|{name}|
|||AWS::RDS::DBSubnetGroup|{name}SubnetGroup|
|`dynamodb`|||||
|||AWS::DynamoDB::Table|{name}|

## Linking resources

Some resources can interact with each other.  You sometimes would like the Lambda function to have access to the S3 bucket, or the DynamoDB table you just created.  Instead of struggling to figure out how to setup the IAM policy for it, CFH will create a basic IAM role for you to do the job.

|**From**|**To**|**Result**|
|--|--|--|
|`parameter`|`lambda`|Use the CloudFormation parameter as an environment variable to the Lambda function|
|`s3`|`lambda`|Add environment variable to the Lambda function<br>Add an IAM policy to the Lambda Execution Role to allow access to the bucket|
|`dynamodb`|`lambda`|Add environment variable to the Lambda function<br>Add an IAM policy to the Lambda Execution Role to allow access to the DynamoDB Table|
|`ssmparameter`|`lambda`|Add environment variable to the SSM Parameter<br>Add an IAM policy to the Lambda Execution Role to allow access to the SSM parameter|
|`s3`|`ec2`|Add an IAM policy to the EC2 Role to allow access to the bucket|
