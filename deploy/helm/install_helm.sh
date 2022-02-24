#!/bin/bash

export HELM_VERSION=`cat ./HELM_VERSION`
curl -fsSL -o helm.tar.gz https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz
tar -zxvf helm.tar.gz -C /usr/local/bin/
chmod +x /usr/local/bin/helm
rm -f helm.tar.gz
