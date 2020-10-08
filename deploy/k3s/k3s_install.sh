#!/bin/bash
PUBLIC_IP=`curl http://169.254.169.254/latest/meta-data/public-ipv4`
INSTALL_K3S_VERSION=`cat ./K3S_VERSION`
INSTALL_K3S_EXEC="--tls-san results.runwaterloo.com --tls-san $PUBLIC_IP"
curl -sfL https://get.k3s.io | sh -