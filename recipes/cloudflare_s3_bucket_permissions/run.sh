#!/bin/sh


tag=cloudflare_s3_bucket_permissions
export CFH="python ../../cfh.py"

rm ../$tag.json

$CFH -cf ../$tag.json -desc "Update S3 bucket permissions to allow Cloudflare CDN to consume the web traffic"
$CFH -cf ../$tag.json -add lambda updateCloudFlareIP
$CFH -cf ../$tag.json -add eventbridge updateCloudFlareIPSchedule -cron "rate(1 day)" -target updateCloudFlareIP