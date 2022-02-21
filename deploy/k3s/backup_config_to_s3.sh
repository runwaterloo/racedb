#!/bin/bash
# This assumes you have an S3 envar $BUCKET
aws s3 cp /etc/rancher/k3s/k3s.yaml s3://${BUCKET}/k3s/k3s.yaml
