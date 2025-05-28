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

# configure node exporter
NE_VER=1.0.1
wget https://github.com/prometheus/node_exporter/releases/download/v${NE_VER}/node_exporter-${NE_VER}.linux-amd64.tar.gz
tar zxvf node_exporter-${NE_VER}.linux-amd64.tar.gz
cp -ap node_exporter-${NE_VER}.linux-amd64/node_exporter /usr/local/bin/
rm -rf node_exporter*
cp /srv/racedb/deploy/aws/node_exporter.service /etc/systemd/system/node_exporter.service
systemctl daemon-reload
systemctl enable node_exporter
systemctl start node_exporter

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

# deploy traefik
cd ../traefik
./create_cloudflare_secrets.sh
./deploy.sh

# set KUBECONFIG envar in Gitlab
K=`cat /etc/rancher/k3s/k3s.yaml`
GITLAB_KUBECONFIG=${K/127.0.0.1/results.runwaterloo.com}
curl --request PUT --header "PRIVATE-TOKEN: ${PERSONAL_ACCESS_TOKEN}" \
     "https://gitlab.com/api/v4/projects/${PROJECT_ID}/variables/KUBECONFIG" --form "value=${GITLAB_KUBECONFIG}"

# get latest tag from gitlab
LATEST_TAG=`curl --header "PRIVATE-TOKEN: ${PERSONAL_ACCESS_TOKEN}" "https://gitlab.com/api/v4/projects/${PROJECT_ID}/repository/tags/" | jq -r '.[0].name'`

# deploy rrw with helm
cd ../helm
helm upgrade --install racedb . --values values-rrw.yaml --set image.tag="${LATEST_TAG:1}"

# dev environment
apt-get -y install python3-pip
./restore-secrets-racedb.sh
rm -rf .kube
helm upgrade --install racedbdev . --values values-racedb.yaml --set image.tag="${LATEST_TAG:1}"
runuser -l ubuntu -c "git config --global user.name \"${GIT_USER}\""
runuser -l ubuntu -c "git config --global user.email \"${GIT_EMAIL}\""
runuser -l ubuntu -c 'python3 -m pip install pre-commit'
runuser -l ubuntu -c 'cd /srv/racedb; /home/ubuntu/.local/bin/pre-commit install'
echo 'PATH=$PATH:/srv/racedb/deploy/misc/' >> /home/ubuntu/.profile

# setup autorecovery
REGION="us-east-1"
INSTANCE_ID=`curl http://169.254.169.254/latest/meta-data/instance-id`
aws --region $REGION cloudwatch put-metric-alarm --alarm-name autorecovery --metric-name StatusCheckFailed_System --namespace AWS/EC2 --statistic Maximum --dimensions Name=InstanceId,Value=${INSTANCE_ID} --unit Count --period 60 --evaluation-periods 3 --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold --alarm-actions arn:aws:automate:${REGION}:ec2:recover

# deploy alloy
cd ../alloy
sed -i "s/LOKI_USERNAME/${LOKI_USERNAME}/g" values.yaml
sed -i "s/PROM_USERNAME/${PROM_USERNAME}/g" values.yaml
sed -i "s/GRAFANA_API_TOKEN/${GRAFANA_API_TOKEN}/g" values.yaml
sed -i "s/MYSQL_DATA_SOURCE_NAME/${MYSQL_DATA_SOURCE_NAME}/g" values.yaml
./deploy.sh

echo "SUCCESS: deploy_rrw.sh completed"
