# This should go in user data in the launch template in AWS.
# The intention is to keep this to a minimum so that most things
# are controlled by code. Substitute actual values in the
# <placeholders>.

#!/bin/bash
export BUCKET=<private_bucket>
export PROJECT_ID=<gitlab_project_id>
export PERSONAL_ACCESS_TOKEN=<gitlab_personal_access_token>
export GIT_USER=<git_user>
export GIT_EMAIL=<git_password>
apt-get update
apt-get -y install awscli git jq
aws s3 cp --recursive s3://${BUCKET}/ubuntu-ssh/ /home/ubuntu/.ssh/
chown -R ubuntu:ubuntu /home/ubuntu/.ssh
chmod 600 /home/ubuntu/.ssh/authorized_keys /home/ubuntu/.ssh/id_rsa
chmod 644 /home/ubuntu/.ssh/known_hosts /home/ubuntu/.ssh/id_rsa.pub
mkdir /srv/racedb
chown ubuntu:ubuntu /srv/racedb
runuser -l ubuntu -c 'git clone git@gitlab.com:sl70176/racedb.git /srv/racedb'
/srv/racedb/deploy/aws/deploy_rrw.sh
