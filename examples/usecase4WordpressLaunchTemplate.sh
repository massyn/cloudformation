#!/usr/bin/bash

# == Experimental code 
export DBServer=##myDatabase:DNSName##
export DBUsername=##myDatabaseMasterUsername##
export DBPassword=##myDatabaseMasterUserPassword##

# == let's start installing some stuff...
yum update -y
yum install python3 git -y

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# == install nginx
yum install amazon-linux-extras -y
sudo amazon-linux-extras enable epel
sudo yum install -y epel-release
sudo yum install -y nginx
sudo systemctl enable nginx

export WWWROOT=/usr/share/nginx/html

# == Install PHP
sudo amazon-linux-extras install php8.0

# == harden the web server

echo "server_tokens off;">/etc/nginx/default.d/security.conf
echo "add_header X-Frame-Options \"SAMEORIGIN\";">>/etc/nginx/default.d/security.conf
echo "add_header Strict-Transport-Security \"max-age=31536000; includeSubdomains; preload\";">>/etc/nginx/default.d/security.conf
# We don't need this -- this is only for troubleshooting load balancing instances
#echo "add_header hostname \"$HOSTNAME\";">>/etc/nginx/default.d/security.conf

cp /etc/php.ini /etc/php.ini.orig
cat /etc/php.ini.orig | grep -v expose_php > /etc/php.ini
echo "expose_php = Off" >> /etc/php.ini
service php-fpm restart

# == install wordpress
# == This is to demonstrate what is possible.  While you will be able to get Wordpress
# == running, it won't stay up when the instance is rebooted.  Wordpress typically creates
# == local configuration files, which will be lost when the instance is terminated.
# == You will be better off copying the files over from an S3 bucket
# aws s3 sync s3://YOURS3BUCKET $WWWROOT

rm -rf $WWWROOT
mkdir $WWWROOT
curl "https://wordpress.org/latest.tar.gz" -o latest.tar.gz
tar -xzf latest.tar.gz
mv wordpress/* $WWWROOT
chown -R apache:apache $WWWROOT

# Allow things to install, then we restart nginx
sleep 30
sudo service nginx start