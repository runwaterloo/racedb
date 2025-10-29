#!/bin/bash

./create_secret.sh
kubectl apply -f ./manifests
