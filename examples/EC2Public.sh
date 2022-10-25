#!/usr/bin/bash

yum update -y
yum install python3 git -y

curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

yum install -y httpd
systemctl enable httpd
sudo yum install -y mod_ssl
cd /etc/pki/tls/certs && sudo ./make-dummy-cert localhost.crt
mv /etc/httpd/conf.d/ssl.conf /etc/httpd/conf.d/ssl.conf.orig
cat /etc/httpd/conf.d/ssl.conf.orig | grep -v SSLCertificateKeyFile > /etc/httpd/conf.d/ssl.conf
echo "EC2 public instance" > /var/www/html/index.html
service httpd start