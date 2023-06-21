#!/bin/bash

# Update requirements.txt
pip install pip-review
pip-review --local --interactive

# Check for changes
if git diff --exit-code --quiet -- requirements.txt; then
    echo "No changes to requirements.txt"
else
    echo "requirements.txt updated, creating Merge Request"

    # Git configuration (replace with your username and email)
    git config --global user.name "Dependency Updater"
    git config --global user.email "dependency-updater@scrw.ca"

    # Create a new branch and commit changes
    git checkout -b update-dependencies
    git add requirements.txt
    git commit -m "Update dependencies"

    # Push the branch to the remote repository
    git push -u origin update-dependencies

    # Use GitLab's API to create a Merge Request (replace with your GitLab private token, project ID, and desired MR title and description)
    curl --header "PRIVATE-TOKEN: <your_private_token>" -X POST "https://gitlab.com/api/v4/projects/<project_id>/merge_requests" -d "source_branch=update-dependencies" -d "target_branch=master" -d "title=<MR title>" -d "description=<MR description>"
fi
