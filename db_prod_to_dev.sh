#!/bin/bash
echo "WARNING: This will replace the test database with data from production!"
read -p "Are you sure (y/n)? " -r
echo    # (optional) move to a new line
if [[ $REPLY = "y" ]]
then
    ssh roanne.scrw.ca "sudo /usr/bin/mysqldump racedb" | sudo mysql racedb
fi
