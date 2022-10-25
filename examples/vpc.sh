#!/usr/bin/sh

rm vpc.json
python ../cfh.py -cf vpc.json -desc "Showing how a VPC works"
python ../cfh.py -cf vpc.json -add vpc myVPC -cidr 10.0.0.0/22

# -- setup the public subnets
python ../cfh.py -cf vpc.json -add publicsubnet myPublicSubnetA -az 0 -cidr 10.0.0.0/24
python ../cfh.py -cf vpc.json -add publicsubnet myPublicSubnetB -az 1 -cidr 10.0.1.0/24

# -- setup the private subnets
python ../cfh.py -cf vpc.json -add natgateway myNatGateway -subnet myPublicSubnetA
python ../cfh.py -cf vpc.json -add privatesubnet myPrivateSubnetA -az 0 -cidr 10.0.2.0/24 -routetable myNatGatewayRouteTableNATGateway
python ../cfh.py -cf vpc.json -add privatesubnet myPrivateSubnetB -az 1 -cidr 10.0.3.0/24 -routetable myNatGatewayRouteTableNATGateway

python ../cfh.py -cf vpc.json -add securitygroup mySecurityGroup
python ../cfh.py -cf vpc.json -add ec2 EC2Private -subnet myPrivateSubnetA -sg mySecurityGroup
python ../cfh.py -cf vpc.json -add ec2 EC2Public -subnet myPublicSubnetA -sg mySecurityGroup

python ../cfh.py -cf vpc.json -properties EC2Private KeyName ap-southeast-2-2022

# -- Create a launch template
python ../cfh.py -cf vpc.json -add launchtemplate myLaunchTemplate

# -- Add it to an autoscaling group
python ../cfh.py -cf vpc.json -add autoscaling myAutoscalingGroup -lt myLaunchTemplate -subnet myPublicSubnetA,myPublicSubnetB

# -- create some s3 buckets
python ../cfh.py -cf vpc.json -add s3 myS3Bucket
python ../cfh.py -cf vpc.json -add static myStaticSite

# -- create a Lambda function
python ../cfh.py -cf vpc.json -add lambda myLambdaFunction

# -- trigger it every minute
python ../cfh.py -cf vpc.json -add eventbridge myEventBridge -cron "rate(5 minutes)" -target myLambdaFunction

python ../cfh.py -cf vpc.json -link myStaticSite myLambdaFunction

# -- Push out the stack
python ../cfh.py -cf vpc.json -updatestack YOURSTACKNAME
