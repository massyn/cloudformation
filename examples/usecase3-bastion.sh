#!/usr/bin/bash

rm usecase3.json
python ../cfh.py -cf usecase3.json -desc "Use case 3 - Bastion server"

python ../cfh.py -cf usecase3.json -add securitygroup SGBastion -ingress 0.0.0.0/0 -tcp 22
python ../cfh.py -cf usecase3.json -add securitygroup SGBastion -egress 0.0.0.0/0

python ../cfh.py -cf usecase3.json -add ec2 BastionServer -sg SGBastion

python ../cfh.py -cf usecase3.json -properties BastionServer KeyName ap-southeast-2-2022