#!/bin/bash

# DU_ACCESS_TOKEN needs to be set in the environment

# Update requirements.txt
pip install pur
pur

# Check for changes
if git diff --exit-code --quiet -- requirements.txt; then
    echo "No changes to requirements.txt"
    exit
else
    echo "requirements.txt updated, creating Merge Request"

    # read the version from the file
    version=$(cat version.txt)

    # extract the parts of the version number
    old_year=$(echo $version | cut -d'.' -f1)
    old_month=$(echo $version | cut -d'.' -f2)
    old_increment=$(echo $version | cut -d'.' -f3)

    # get the current date
    current_year=$(date +"%y")
    current_month=$(date +"%-m")

    # compare the dates and update the version accordingly
    if [[ "$current_year" -gt "$old_year" ]] || [[ "$current_year" -eq "$old_year" && "$current_month" -gt "$old_month" ]]
    then
        # the current year or month is greater than the old one, so reset the increment
        new_version="${current_year}.${current_month}.0"
    else
        # the current year and month match the old ones, so increment the old increment
        new_increment=$((old_increment+1))
        new_version="${old_year}.${old_month}.${new_increment}"
    fi

    # save the new version to the file
    echo $new_version > version.txt

    # Git configuration (replace with your username and email)
    git config --global user.name "Dependency Updater"
    git config --global user.email "du-no-reply@scrw.ca"

    # Create a new branch and commit changes
    git checkout -b update-dependencies
    git add requirements.txt version.txt
    git commit -m "Update dependencies"

    # Push the branch to the remote repository
    git remote set-url origin ${CI_PROJECT_URL/gitlab.com/oauth2:${DU_ACCESS_TOKEN}@gitlab.com}.git
    git push -u origin update-dependencies

    # Use GitLab's API to create a Merge Request (replace with your GitLab private token, project ID, and desired MR title and description)
    curl --header "PRIVATE-TOKEN: $DU_ACCESS_TOKEN" -X POST "https://gitlab.com/api/v4/projects/2322084/merge_requests" -d "source_branch=update-dependencies" -d "target_branch=main" -d "title=Update dependencies"
fi
