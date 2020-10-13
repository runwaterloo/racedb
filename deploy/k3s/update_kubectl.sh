#!/bin/bash
BUCKET=$1
IPADDR=$2
mv ~/.kube/config ~/.kube/config.$$
aws --profile js s3 cp s3://${BUCKET}/k3s/k3s.yaml ~/.kube/config
sed -i "s/127.0.0.1/${IPADDR}/g" ~/.kube/config