#!/bin/bash
echo "WARNING: This will replace the production database with data from test!"
read -p "Are you REALLY sure (YES/n)? " -r
echo    # (optional) move to a new line
if [[ $REPLY = "YES" ]]
then
    sudo /usr/bin/mysqldump racedb | ssh roanne.scrw.ca "sudo mysql racedb"
fi
