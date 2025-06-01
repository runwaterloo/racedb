#!/bin/bash

# Check if CI_COMMIT_BRANCH equals CI_DEFAULT_BRANCH
if [ "$CI_COMMIT_BRANCH" != "$CI_DEFAULT_BRANCH" ]; then
  echo "Skipping tag.sh outside of $CI_DEFAULT_BRANCH branch"
  exit 0
fi

# tag/push latest
docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA $CI_REGISTRY_IMAGE:latest
docker push $CI_REGISTRY_IMAGE:latest

# tag/push version
docker tag $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA $CI_REGISTRY_IMAGE:${VERSION}
docker push $CI_REGISTRY_IMAGE:${VERSION}

# tag branch
git tag ${VERSION}
git remote set-url origin ${CI_PROJECT_URL/gitlab.com/oauth2:${DEPUP_TOKEN}@gitlab.com}.git
git push --tags
