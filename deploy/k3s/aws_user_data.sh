#!/bin/bash
export BUCKET=<private_bucket>
export GIT_CLONE_URL=https://gitlab+deploy-token-XXXXXX:YYYYYYYYYY@gitlab.com/sl70176/racedb.git
apt-get update
apt-get -y install awscli git
git clone $GIT_CLONE_URL
cd racedb/deploy/k3s
./k3s_install.sh
./racedb_deploy.sh
cd
rm -rf racedb