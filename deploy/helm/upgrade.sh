#!/bin/bash

set -e

if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <deployment> <values-file> <tag>"
    exit 1
fi

export DEPLOYMENT="$1"
export VALUES_FILE="$2"
export TAG="$3"

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

helm upgrade --install "$DEPLOYMENT" . \
    --values "$VALUES_FILE" \
    --set image.tag="$TAG" \
    --wait --timeout 10m;

# Run clear_cache in a ready web pod only after every web AND celery pod
# runs the new $TAG and is ready. clear_cache enqueues warm_cache via the
# broker, and celery is the consumer -- enqueueing while old pods are
# still terminating is how the warm task got lost on 2026-10-28 (the
# dying worker consumed the message before the new worker connected),
# leaving prod cache-cold for visitors. Converge first, then clear.
wait_for_convergence() {
    # $1 = pod task label. Expected count is re-queried every iteration:
    # during a rollout the total includes terminating old pods, and that
    # number shrinks as they exit -- a stale count would never converge.
    for i in $(seq 1 60); do
        total=$(kubectl get pods -l app.kubernetes.io/instance="$DEPLOYMENT",app.kubernetes.io/name=racedb,app.kubernetes.io/task="$1" \
            --field-selector=status.phase=Running -o json 2>/dev/null | jq '.items | length')
        found=$(kubectl get pods -l app.kubernetes.io/instance="$DEPLOYMENT",app.kubernetes.io/name=racedb,app.kubernetes.io/task="$1" \
            --field-selector=status.phase=Running \
            -o jsonpath='{range .items[*]}{.status.containerStatuses[0].image}{"|"}{.status.containerStatuses[0].ready}{"|"}{.metadata.deletionTimestamp}{"|"}{.metadata.name}{"\n"}{end}' 2>/dev/null \
            | awk -F'|' -v tag="$TAG" \
                '$1 ~ (":" tag "$") && $2=="true" && $3=="" {n++} END {print n+0}')
        if [ "$found" = "$total" ] && [ "$total" -gt 0 ]; then
            echo "All $total $1 pod(s) running tag $TAG, ready and not terminating"
            return 0
        fi
        echo "Waiting for $1 pod(s) at tag $TAG, ready and not terminating (found $found of $total, attempt $i/60)"
        sleep 10
    done
    echo "ERROR: $1 pods never converged to tag $TAG; not running clear_cache"
    return 1
}

if ! wait_for_convergence web; then exit 1; fi
if ! wait_for_convergence celery; then exit 1; fi

POD=$(kubectl get pods -l app.kubernetes.io/instance="$DEPLOYMENT",app.kubernetes.io/name=racedb,app.kubernetes.io/task=web \
    --field-selector=status.phase=Running \
    -o jsonpath='{range .items[*]}{.status.containerStatuses[0].image}{"|"}{.status.containerStatuses[0].ready}{"|"}{.metadata.deletionTimestamp}{"|"}{.metadata.name}{"\n"}{end}' \
    | awk -F'|' -v tag="$TAG" '$1 ~ (":" tag "$") && $2=="true" && $3==""{print $4; exit}')
if [ -z "$POD" ]; then
    echo "ERROR: no ready web pod at tag $TAG found for clear_cache"
    exit 1
fi
echo "Running python manage.py clear_cache in pod $POD"
kubectl exec "$POD" -- python manage.py clear_cache
