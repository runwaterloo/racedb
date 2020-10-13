#!/bin/bash
export PUBLIC_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4`
export INSTALL_K3S_VERSION=`cat ./K3S_VERSION`
export INSTALL_K3S_EXEC="--no-deploy=traefik --tls-san results.runwaterloo.com --tls-san $PUBLIC_IP"
curl -sfL https://get.k3s.io | sh -
aws s3 cp /etc/rancher/k3s/k3s.yaml s3://${BUCKET}/k3s/k3s.yaml
mkdir -p /traefik/etc
aws s3 cp s3://${BUCKET}/traefik/acme.json /traefik/etc/acme.json
chmod 600 /traefik/etc/acme.json
kubectl apply -f ./traefik_yaml