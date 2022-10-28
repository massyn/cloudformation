#!/usr/bin/bash

yum update -y
yum install python3 git -y

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

yum install -y httpd
systemctl enable httpd
sudo yum install -y mod_ssl 
yum install amazon-linux-extras -y

sudo amazon-linux-extras enable php7.4 

sudo yum clean metadata 
sudo yum install -y php php-common php-pear 
sudo yum install -y php-cli php-pdo php-fpm php-json php-mysqlnd

cd /etc/pki/tls/certs && sudo ./make-dummy-cert localhost.crt
mv /etc/httpd/conf.d/ssl.conf /etc/httpd/conf.d/ssl.conf.orig
cat /etc/httpd/conf.d/ssl.conf.orig | grep -v SSLCertificateKeyFile > /etc/httpd/conf.d/ssl.conf

rm /var/www/html/index.html
service httpd start

# == install wordpress
curl "https://wordpress.org/latest.tar.gz" -o latest.tar.gz
tar -xzf latest.tar.gz
mv wordpress/*  /var/www/html/


