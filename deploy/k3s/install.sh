#!/bin/bash

# check for AWS IP address
export PUBLIC_IP=`curl --max-time 3 http://169.254.169.254/latest/meta-data/public-ipv4`
if [ -z "$PUBLIC_IP" ]
then
      PUBLIC_TLS_SAN=""
else
      PUBLIC_TLS_SAN="--tls-san $PUBLIC_IP"
fi

# setup install envars
export INSTALL_K3S_VERSION=`cat ./K3S_VERSION`
export INSTALL_K3S_EXEC="--disable=traefik --tls-san results.runwaterloo.com $PUBLIC_TLS_SAN"
export K3S_KUBECONFIG_MODE="644"

# install k3s
curl -sfL https://get.k3s.io | sh -
