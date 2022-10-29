#!/bin/sh

rm wordpress.json
python ../cfh.py -cf wordpress.json -desc "Complex Wordpress example"

python ../cfh.py -cf wordpress.json -add vpc myVPC -cidr 10.0.0.0/22
python ../cfh.py -cf wordpress.json -add publicsubnet myPublicSubnetA -az 0 -vpc myVPC -cidr 10.0.0.0/24
python ../cfh.py -cf wordpress.json -add publicsubnet myPublicSubnetB -az 1 -vpc myVPC -cidr 10.0.1.0/24

# -- inbound web traffic
python ../cfh.py -cf wordpress.json -add securitygroup SGWebInbound -vpc myVPC -ingress 0.0.0.0/0 -tcp 80
python ../cfh.py -cf wordpress.json -add securitygroup SGWebInbound -vpc myVPC -ingress 0.0.0.0/0 -tcp 443
python ../cfh.py -cf wordpress.json -add securitygroup SGWebInbound -vpc myVPC -egress 0.0.0.0/0

# -- ELBtoWeb
python ../cfh.py -cf wordpress.json -add securitygroup SGWebServer -vpc myVPC -ingress SGWebInbound -tcp 80
python ../cfh.py -cf wordpress.json -add securitygroup SGWebServer -vpc myVPC -ingress SGWebInbound -tcp 443
python ../cfh.py -cf wordpress.json -add securitygroup SGWebServer -vpc myVPC -egress 0.0.0.0/0

# -- Web to database traffic
python ../cfh.py -cf wordpress.json -add securitygroup SGdatabase -vpc myVPC -egress 0.0.0.0/0
python ../cfh.py -cf wordpress.json -add securitygroup SGdatabase -vpc myVPC -ingress SGWebServer -tcp 3306

# -- create a single web server
#python ../cfh.py -cf wordpress.json -add ec2 EC2WebServer1 -subnet myPublicSubnetA -sg SGWebInbound

# -- a better way is to create a launch template in a private subnet, so it simply stays up
# -- lets create a NAT gateway, else our private instances wont be able to update or install
python ../cfh.py -cf wordpress.json -add natgateway myNatGateway -subnet myPublicSubnetA

# -- create the private subnet linked to the NAT gateway
python ../cfh.py -cf wordpress.json -add privatesubnet myPrivateSubnetA -az 0 -vpc myVPC -cidr 10.0.2.0/24 -routetable myNatGatewayRouteTableNATGateway
python ../cfh.py -cf wordpress.json -add privatesubnet myPrivateSubnetB -az 1 -vpc myVPC -cidr 10.0.3.0/24 -routetable myNatGatewayRouteTableNATGateway

# -- Create a launch template

python ../cfh.py -cf wordpress.json -add launchtemplate LaunchTemplate -sg SGWebServer
python ../cfh.py -cf wordpress.json -add autoscaling myAutoscalingGroup -lt LaunchTemplate -subnet myPrivateSubnetA,myPrivateSubnetB -vpc myVPC

# -- create a load balancer
python ../cfh.py -cf wordpress.json -add elbv2 myELBv2 -sg SGWebInbound -subnet myPublicSubnetA,myPublicSubnetB

# -- create the database

python ../cfh.py -cf wordpress.json -add rds myDatabase -subnet myPrivateSubnetA,myPrivateSubnetB -sg SGdatabase

