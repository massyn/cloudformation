#!/usr/bin/sh

rm usecase1.json

python ../cfh.py -cf usecase1.json -desc "Use case 1 - Function URL to DynamoDB example"
python ../cfh.py -cf usecase1.json -add lambda usecase1lambda
python ../cfh.py -cf usecase1.json -add functionurl myFunctionUrl -target usecase1lambda
python ../cfh.py -cf usecase1.json -add dynamodb myDynamoDbTable
python ../cfh.py -cf usecase1.json -link myDynamoDbTable usecase1lambda
