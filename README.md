# CloudFormation Helper
Cloudformation Helper script

## What is CloudFormation Helper?

CloudFormation Helper is a tool to help you add resources to CloudFormation templates, create basic links between resources, or update code used in EC2 UserData, or Lambda functions.

This tool uses no state files and does not know your AWS environment.  It is simply a tool that touches your CloudFormation json file by adding (or slightly modifying existing) resources.  The basic idea of the tool is to stand up some basic infrastructure, and allow you to then customise the CloudFormation template how you see fit.

It also has the built-in capability to update Lambda function code, or EC2 UserData, without requiring you manually edit the files.

CFH is not intended to be a replacement for tools like Teraform or CDK, which are already much more advanced and mature than CFH.  This tool is for situations where the result is a CloudFormation template, and you require some assistance to add some resources to the template.  Instead of simply disregarding all the good work you've already done, where a need exists to create a new CloudFormation template from scratch, you can use CFH to do some of the heavy lifting for you.

## Features of the tool

* Adding resources
* Listing all resources
* Adding parameters
* Linking dependencies
* Updating Lambda functions code
* Updating EC2 UserData

## Wish list for a future version

* Use yaml files instead of json
* Add docker containers
* Add DynamoDB tables
* Add RDS
* Add a few more security group templates
* Add a load balancer
* Add lambda URLs
* Add API Gateway

### Linking

* EC2 Roles to S3
* EC2 Roles to Lambda
* API Gateway to Lambda

## -add resource options

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
|`autoscaling`|`-lt` `-subnets`||||
|||AWS::AutoScaling::AutoScalingGroup|{name}|
|`eventbridge`|`-cron` `-target`||||
|||AWS::Events::Rule|{name}|
|||AWS::Lambda::Permission|{name}lambdaPermission|

## Basic Usage

### Create your first CloudFormation template

`cfh.py -cf myCloudFormationFile.json -desc "This is my first template"`

### Adding Resources

Resources within CFH can be added with the `-add` option

#### s3

Creates a basic S3 bucket, with public access denied

`cfh.py -cf myCloudFormationFile.json -add s3 myS3Bucket`

#### static

* Creates a basic S3 bucket with web access enabled
* Attaches a bucket policy to allow public access
* Outputs the website URL as an output

`cfh.py -cf myCloudFormationFile.json -add static myS3Website`

#### lambda

Creating a basic Python 3.9 Lambda function

* Creates a Lambda function for Python 3.9
* Creates a basic Lambda Execution Role, and attaches it to the function

`cfh.py -cf myCloudFormationFile.json -add lambda myLambdaFunction`

##### Refreshing Lambda code

CFH will check if a file called `{name}.py` exists - if it does, it will replace the `Code` section of the template with the contents of this file.

#### launchtemplate

* Creates an EC2 role
* Creates an EC2 Instance Profile linked to the EC2 role
* Creates a parameter to retrieve the latest Amazon Linux 2 AMI from the SSM Parameter Store

#### Refreshing UserData

CFH will check if a file called `{name}.sh` exists - if it does, it will replace the `UserData` section of the template with the contents of this file.

#### Asking for a Security Group

Without specifying the `-sg` parameter, CFH will create a launch template, and generate a parameter to request the security group to be used.

`cfh.py -cf myCloudFormationFile.json -add launchtemplate myLaunchTemplate`

#### Providing a Security Group

By specifying the `-sg` option, you can provide the resource reference to a security group to use instead of asking for it from the Parameter section.

`cfh.py -cf myCloudFormationFile.json -add launchtemplate myLaunchTemplate -sg mySecurityGroup`

#### ec2

* Creates an EC2 Role
* Creates an EC2 Instance Profile
* Creates an EC2 Instance

##### Refreshing UserData

CFH will check if a file called `{name}.sh` exists - if it does, it will replace the `UserData` section of the template with the contents of this file.

##### Asking for a Security Group

Without specifying the `-sg` parameter, CFH will create an EC2 instance, and generate a parameter to request the security group to be used.

`cfh.py -cf myCloudFormationFile.json -add ec2 myEC2instance -subnet myVPCSubnetA0`

##### Providing a Security Group

By specifying the `-sg` option, you can provide the resource reference to a security group to use instead of asking for it from the Parameter section.

`cfh.py -cf myCloudFormationFile.json -add ec2 myEC2instance -sg mySecurityGroup`

#### autoscaling

* Creates an Autoscaling group
* Creates a parameter to ask for Subnets to use (if -subnet is not specified)

Create an autoscaling group linked to a launch template.  If only 1 launch template exists, the autoscaling group will use it.

`cfh.py -cf myCloudFormationFile.json -add autoscaling myAutoScalingGroup -subnet myVPCSubnetA0`

If more than one launch template exists, specify the one to use with the `-lt` option.

`cfh.py -cf myCloudFormationFile.json -add autoscaling myAutoScalingGroup -lt myLaunchTemplate`

#### securitygroup

* Creates a Security Group
* Creates a parameter to ask for a VpcId to use, or use the default VPC it finds in the template

`cfh.py -cf myCloudFormationFile.json -add securitygroup mySecurityGroup`

This template creates an inbound Port 80 / 443 (Web) security group.

TODO - Create a few more templates, like database use, etc.

#### natgateway

Creates a NAT gateway, Elastic IP.  Also needs `-subnet` parameter

`cfh.py -cf myCloudFormationFile.json -add natgateway myNATgateway -subnet myVPCSubnetA1`

#### vpc

* Creates a VPC of cidr 10.0.0./22
* Creates 2 public subnets (10.0.0.0/24, 10.0.1.0/24)
* Creates 2 private subnets (10.0.2.0/24, 10.0.3.0/24)
* Creates an internet gateway
* Creates a route table
* Creates routes to all subnets

`cfh.py -cf myCloudFormationFile.json -add vpc myVPC`

||**AZ 1**|**AZ 2**|
|--|--|--|
|Public|10.0.0.0/24|10.0.1.0/24|
|Private|10.0.2.0/24|10.0.3.0/24|

## Linking resources

Some resources can interact with each other.

### s3 lambda

* Grants the Lambda function Execution Role permissions to consume the S3 bucket
* Includes the S3 bucket name as an environment variable on the Lambda function

### lambda dynamodb (TODO)

* Grants the Lambda function Execution Role permissions to consume the dynamodb table
* Includes the dynamodb table name as an environment variable on the Lambda function

