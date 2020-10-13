#!/bin/bash

# setup swap
fallocate -l 1G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile swap swap defaults 0 0" >> /etc/fstab

# setup envars
export PUBLIC_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4`
export INSTALL_K3S_VERSION=`cat ./K3S_VERSION`
export INSTALL_K3S_EXEC="--no-deploy=traefik --tls-san results.runwaterloo.com --tls-san $PUBLIC_IP"

# install k3s
curl -sfL https://get.k3s.io | sh -

# backup config to S3
aws s3 cp /etc/rancher/k3s/k3s.yaml s3://${BUCKET}/k3s/k3s.yaml

# restore traefik certrs
mkdir -p /traefik/etc
aws s3 cp s3://${BUCKET}/traefik/acme.json /traefik/etc/acme.json
chmod 600 /traefik/etc/acme.json

# install traefik
kubectl apply -f ./traefik_yaml