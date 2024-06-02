#!/bin/bash

cd deploy/helm
sh ./install_helm.sh
echo "$KUBECONFIG" > /kubeconfig
export KUBECONFIG=/kubeconfig

if [ "$CI_COMMIT_BRANCH" == "$CI_DEFAULT_BRANCH" ]; then
  /usr/local/bin/helm upgrade racedb . --values values-rrw.yaml --set image.tag="${VERSION}" --wait
  curl --retry 6 "https://results.runwaterloo.com/cache_clear/?notifykey=${NOTIFYKEY}"
  /usr/local/bin/helm upgrade racedbdev . --values values-racedb.yaml --set image.tag="${VERSION}" --wait
  curl --retry 6 "https://racedb.runwaterloo.com/cache_clear/?notifykey=${NOTIFYKEY}"
else
  /usr/local/bin/helm upgrade racedbdev . --values values-racedb.yaml --set image.tag="${CI_COMMIT_SHORT_SHA}" --wait
  curl --retry 6 "https://racedb.runwaterloo.com/cache_clear/?notifykey=${NOTIFYKEY}"
fi
