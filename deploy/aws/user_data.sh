# This should go in user data in the launch template in AWS.
# The intention is to keep this to a minimum so that most things
# are controlled by code. Substitute actual values in the
# <placeholders>.

#!/bin/bash
set -e
export BRANCH=main
export BUCKET=<private_bucket>
export GIT_USER=<git_user>
export GIT_EMAIL=<git_password>
export GRAFANA_API_TOKEN=<grafana_api_token>
export LOKI_USERNAME=<loki_username>
export PROM_USERNAME=<prom_username>
export MYSQL_DATA_SOURCE_NAME=<mysql_data_source_name>
echo "<slack_gitlab_webhook>" > /root/SLACK_GITLAB_WEBHOOK

set -x
apt-get update
apt-get -y install awscli cron git jq vim
aws s3 cp --recursive s3://${BUCKET}/ubuntu-ssh/ /home/ubuntu/.ssh/
mkdir /srv/racedb
chown ubuntu:ubuntu /srv/racedb
runuser -l ubuntu -c "git clone -b $BRANCH https://github.com/runwaterloo/racedb.git /srv/racedb"
/srv/racedb/deploy/aws/deploy_rrw.sh
echo "SUCCESS: user_data script completed"
