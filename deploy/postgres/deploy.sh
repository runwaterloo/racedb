#!/bin/bash

./create_secret.sh
kubectl apply -f ./manifests
kubectl wait --for=condition=ready pod/postgres-0 --timeout=180s
