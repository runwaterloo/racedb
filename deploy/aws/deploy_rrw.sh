#!/bin/bash

set -ex

# setup swap
fallocate -l 1025M /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo "/swapfile swap swap defaults 0 0" >> /etc/fstab

# set swappiness
echo "vm.swappiness = 10" >> /etc/sysctl.conf
sysctl --system

# install helm
cd /srv/racedb/deploy/helm
./install_helm.sh

# install K3S
cd /srv/racedb/deploy/k3s
./install.sh
mkdir ~/.kube 2> /dev/null
cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
./backup_config_to_s3.sh
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# restore rrw secrets
cd ../helm
./restore-secrets-rrw.sh
./restore-secrets-racedb.sh

# deploy traefik
cd ../traefik
./create_cloudflare_secrets.sh
./deploy.sh

# deploy postgres
cd ../postgres
./create_secret.sh
./deploy.sh
./restore_db.sh racedb
./create_dev_db.sh
./refresh_dev_db.sh

# get latest tag from gitlab
LATEST_TAG=$(curl -s https://api.github.com/repos/runwaterloo/racedb/tags | jq -r '.[0].name')

# deploy rrw with helm
cd ../helm
helm upgrade --install racedb . --values values-rrw.yaml --set image.tag="${LATEST_TAG}"

# deploy dev environment
apt-get -y install python3-pip
rm -rf .kube
helm upgrade --install racedbdev . --values values-racedb.yaml --set image.tag="${LATEST_TAG}"

# setup git
runuser -l ubuntu -c 'python3 -m pip install pre-commit'
runuser -l ubuntu -c 'cd /srv/racedb; /home/ubuntu/.local/bin/pre-commit install'
echo 'PATH=$PATH:/srv/racedb/deploy/misc/' >> /home/ubuntu/.profile

# setup autorecovery
REGION="us-east-1"
INSTANCE_ID=`curl http://169.254.169.254/latest/meta-data/instance-id`
aws --region $REGION cloudwatch put-metric-alarm --alarm-name autorecovery --metric-name StatusCheckFailed_System --namespace AWS/EC2 --statistic Maximum --dimensions Name=InstanceId,Value=${INSTANCE_ID} --unit Count --period 60 --evaluation-periods 3 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --alarm-actions arn:aws:automate:${REGION}:ec2:recover

# deploy alloy
cd ../alloy
./create_secret.sh
./deploy.sh

# add upgrade cron job
echo '* * * * * /srv/racedb/deploy/helm/autoupgrade.sh' | crontab -

# add backup cron job (hourly on the 12th minute)
(crontab -l 2>/dev/null; echo '12 * * * * /srv/racedb/deploy/aws/backup_to_s3.sh') | crontab -

# add backup monitor cron job (every 15 minutes)
(crontab -l 2>/dev/null; echo "*/15 * * * * /srv/racedb/deploy/aws/backup_monitor.sh $BUCKET database_backup/racedb.latest.sql.gz") | crontab -

echo "SUCCESS: deploy_rrw.sh completed"
