#!/bin/bash

# tag/push latest
docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA $CI_REGISTRY_IMAGE:latest
docker push $CI_REGISTRY_IMAGE:latest

# tag/push version
docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA $CI_REGISTRY_IMAGE:${VERSION}
docker push $CI_REGISTRY_IMAGE:${VERSION}
