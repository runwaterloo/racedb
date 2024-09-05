#!/bin/bash

# The following environment variables need to be set
# DEPUP_NAME
# DEPUP_EMAIL
# DEPUP_TOKEN

# exit on any error
set -e

# Update requirements.txt
pip install pur
pur --skip Django

# Check for changes
if git diff --exit-code --quiet -- requirements.txt; then
    echo "No changes to requirements.txt"
    exit
else
    echo "requirements.txt updated, creating Merge Request"

    # Git configuration (replace with your username and email)
    git config --global user.name "$DEPUP_NAME"
    git config --global user.email "$DEPUP_EMAIL"

    # Create a new branch and commit changes
    BRANCH="update-dependencies-`date +%s`"
    git checkout -b $BRANCH
    git add requirements.txt
    git commit -m "Update Python package dependencies"

    # Push the branch to the remote repository
    git remote set-url origin ${CI_PROJECT_URL/gitlab.com/oauth2:${DEPUP_TOKEN}@gitlab.com}.git
    git push -u origin $BRANCH

    curl --header "PRIVATE-TOKEN: $DEPUP_TOKEN" -X POST "https://gitlab.com/api/v4/projects/2322084/merge_requests" -d "source_branch=$BRANCH" -d "remove_source_branch=true" -d "target_branch=main" -d "title=Update Python package dependencies"
fi
