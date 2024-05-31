#!/bin/bash

# install git package
apk add git -f

# set version
export VERSION=$(TZ=America/Toronto date +'%y.%-m.%-d%H%M%S')

# pull image
docker pull $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA

# tag/push latest
docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA $CI_REGISTRY_IMAGE:latest
docker push $CI_REGISTRY_IMAGE:latest

# tag/push version
docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA $CI_REGISTRY_IMAGE:${VERSION}
docker push $CI_REGISTRY_IMAGE:${VERSION}

# tag branch
git tag v${VERSION}
git remote set-url origin ${CI_PROJECT_URL/gitlab.com/oauth2:${DEPUP_TOKEN}@gitlab.com}.git
git push --tags
