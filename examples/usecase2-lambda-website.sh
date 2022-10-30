#!/usr/bin/bash

rm usecase2.json

python ../cfh.py -cf usecase2.json -desc "Use case 2 - Scheduled lambda to update a website"
python ../cfh.py -cf usecase2.json -add lambda usecase2lambda
python ../cfh.py -cf usecase2.json -add static myStaticS3
python ../cfh.py -cf usecase2.json -add eventbridge myEventBridge -cron "rate(5 minutes)" -target usecase2lambda
python ../cfh.py -cf usecase2.json -add parameter websiteMessage
python ../cfh.py -cf usecase2.json -add ssmparameter mySSMParameterStore -value "Hello there!"
python ../cfh.py -cf usecase2.json -link myStaticS3 usecase2lambda
python ../cfh.py -cf usecase2.json -link websiteMessage usecase2lambda
python ../cfh.py -cf usecase2.json -link mySSMParameterStore usecase2lambda


