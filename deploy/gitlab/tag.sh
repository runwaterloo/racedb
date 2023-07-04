#!/bin/bash

# install git package
apk add git -f

# confirm that version.txt was modified
if ! git diff-tree --no-commit-id --name-only -r ${CI_COMMIT_SHORT_SHA} | grep version.txt; then
  echo "ERROR: version.txt must be updated to run pipeline on main"
  exit 1
fi

export VERSION=`cat version.txt | xargs`
if [ $(git tag -l "v${VERSION}") ]; then
    echo "Tag v${VERSION} already exists, no need to repeat tasks."
    exit 0
fi

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
