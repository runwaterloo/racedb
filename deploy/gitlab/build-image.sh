#!/bin/bash
docker login -u $GITLAB_CI_USER -p $GITLAB_CI_TOKEN $CI_REGISTRY
docker build --tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA .
