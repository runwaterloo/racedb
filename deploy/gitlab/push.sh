#!/bin/bash
docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA
